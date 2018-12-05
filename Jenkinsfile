def label = "${UUID.randomUUID().toString()}"
def BUILD_FOLDER = "/go"
def github_user = "gkirok"
def docker_user = "gallziguazio"
def git_project = "iguazio_api_examples"

properties([pipelineTriggers([[$class: 'PeriodicFolderTrigger', interval: '2m']])])
podTemplate(label: "${git_project}-${label}", yaml: """
apiVersion: v1
kind: Pod
metadata:
  name: "${git_project}-${label}"
  labels:
    jenkins/kube-default: "true"
    app: "jenkins"
    component: "agent"
spec:
  shareProcessNamespace: true
  containers:
    - name: jnlp
      image: jenkinsci/jnlp-slave
      resources:
        limits:
          cpu: 1
          memory: 2Gi
        requests:
          cpu: 1
          memory: 2Gi
      volumeMounts:
        - name: go-shared
          mountPath: /go
    - name: docker-cmd
      image: docker
      command: [ "/bin/sh", "-c", "--" ]
      args: [ "while true; do sleep 30; done;" ]
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run
        - name: go-shared
          mountPath: /go
  volumes:
    - name: docker-sock
      hostPath:
          path: /var/run
    - name: go-shared
      emptyDir: {}
"""
    ) {
    node("${git_project}-${label}") {
//        currentBuild.displayName = "${git_project}"
//        currentBuild.description = "Will not run with tags created before 4 hours and more."

        withCredentials([
                usernamePassword(credentialsId: '4318b7db-a1af-4775-b871-5a35d3e75c21', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME'),
                string(credentialsId: 'dd7f75c5-f055-4eb3-9365-e7d04e644211', variable: 'GIT_TOKEN')
        ]) {
            def AUTO_TAG
            def TAG_VERSION

            stage('get tag data') {
                container('jnlp') {
                    TAG_VERSION = sh(
                            script: "echo ${TAG_NAME} | tr -d '\\n' | egrep '^v[\\.0-9]*.*\$' | sed 's/v//'",
                            returnStdout: true
                    ).trim()

                    sh "curl -v -H \"Authorization: token ${GIT_TOKEN}\" https://api.github.com/repos/gkirok/${git_project}/releases/tags/v${TAG_VERSION} > ~/tag_version"

                    AUTO_TAG = sh(
                            script: "cat ~/tag_version | python -c 'import json,sys;obj=json.load(sys.stdin);print obj[\"body\"]'",
                            returnStdout: true
                    ).trim()

                    PUBLISHED_BEFORE = sh(
                            script: "tag_published_at=\$(cat ~/tag_version | python -c 'import json,sys;obj=json.load(sys.stdin);print obj[\"published_at\"]'); SECONDS=\$(expr \$(date +%s) - \$(date -d \"\$tag_published_at\" +%s)); expr \$SECONDS / 60 + 1",
                            returnStdout: true
                    ).trim()

                    echo "$AUTO_TAG"
                    echo "$TAG_VERSION"
                    echo "$PUBLISHED_BEFORE"
                }
            }

            if ( TAG_VERSION && PUBLISHED_BEFORE < 240 ) {
//                    def V3IO_TSDB_VERSION = sh(
//                            script: "echo ${TAG_VERSION} | awk -F '-v' '{print \"v\"\$2}'",
//                            returnStdout: true
//                    ).trim()

                stage('prepare sources') {
                    container('jnlp') {
                        sh """
                            cd ${BUILD_FOLDER}
                            git clone https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${github_user}/${git_project}.git src/github.com/v3io/${git_project}
                            cd ${BUILD_FOLDER}/src/github.com/v3io/${git_project}/netops_demo/golang/src/github.com/v3io/demos
                            rm -rf vendor/github.com/v3io/v3io-tsdb/
                            git clone https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${github_user}/v3io-tsdb.git vendor/github.com/v3io/v3io-tsdb
                            cd vendor/github.com/v3io/v3io-tsdb
                            rm -rf .git vendor/github.com/v3io vendor/github.com/nuclio
                        """

//                            git checkout ${V3IO_TSDB_VERSION}
                    }
                }

                stage('build in dood') {
                    container('docker-cmd') {
                        sh """
                            cd ${BUILD_FOLDER}/src/github.com/v3io/${git_project}/netops_demo/golang/src/github.com/v3io/demos
                            docker build . --tag netops-demo-golang:latest --tag ${docker_user}/netops-demo-golang:${TAG_VERSION} --build-arg NUCLIO_BUILD_OFFLINE=true --build-arg NUCLIO_BUILD_IMAGE_HANDLER_DIR=github.com/v3io/demos

                            cd ${BUILD_FOLDER}/src/github.com/v3io/${git_project}/netops_demo/py
                            docker build . --tag netops-demo-py:latest --tag ${docker_user}/netops-demo-py:${TAG_VERSION}
                        """
                        withDockerRegistry([credentialsId: "472293cc-61bc-4e9f-aecb-1d8a73827fae", url: ""]) {
                            sh "docker push ${docker_user}/netops-demo-golang:${TAG_VERSION}"
                            sh "docker push ${docker_user}/netops-demo-py:${TAG_VERSION}"
                        }
                    }
                }

                stage('git push') {
                    container('jnlp') {
                        try {
                            sh """
                                git config --global user.email '${GIT_USERNAME}@iguazio.com'
                                git config --global user.name '${GIT_USERNAME}'
                                cd ${BUILD_FOLDER}/src/github.com/v3io/${git_project}/netops_demo
                                git add *
                                git commit -am 'Updated TSDB to latest';
                                git push origin master
                            """
                        } catch (err) {
                            echo "Can not push code to git"
                        }
                    }
                }
            } else {
                stage('warning') {
                    if (PUBLISHED_BEFORE >= 240) {
                        echo "Tag too old, published before $PUBLISHED_BEFORE minutes."
                    } else if (AUTO_TAG.startsWith("Autorelease")) {
                        echo "Autorelease does not trigger this job."
                    } else {
                        echo "${TAG_VERSION} is not release tag."
                    }
                }
            }
        }
    }
}