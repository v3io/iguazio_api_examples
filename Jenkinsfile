label = "${UUID.randomUUID().toString()}"
BUILD_FOLDER = "/go"
docker_user = "iguaziodocker"
docker_credentials = "iguazio-prod-docker-credentials"
git_project = "iguazio_api_examples"
git_project_user = "v3io"
git_deploy_user = "iguazio-prod-git-user"
git_deploy_user_token = "iguazio-prod-git-user-token"

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
        withCredentials([
                usernamePassword(credentialsId: git_deploy_user, passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME'),
                string(credentialsId: git_deploy_user_token, variable: 'GIT_TOKEN')
        ]) {
            def AUTO_TAG
            def TAG_VERSION

            stage('get tag data') {
                container('jnlp') {
                    TAG_VERSION = sh(
                            script: "echo ${TAG_NAME} | tr -d '\\n' | egrep '^v[\\.0-9]*.*\$' | sed 's/v//'",
                            returnStdout: true
                    ).trim()

                    sh "curl -v -H \"Authorization: token ${GIT_TOKEN}\" https://api.github.com/repos/${git_project_user}/${git_project}/releases/tags/v${TAG_VERSION} > ~/tag_version"

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
                stage('prepare sources') {
                    container('jnlp') {
                        sh """
                            cd ${BUILD_FOLDER}
                            git clone https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${git_project_user}/${git_project}.git src/github.com/v3io/${git_project}
                        """
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
                    }
                }

                stage('push to hub') {
                    container('docker-cmd') {
                        withDockerRegistry([credentialsId: docker_credentials, url: ""]) {
                            sh "docker push ${docker_user}/netops-demo-golang:${TAG_VERSION}"
                            sh "docker push ${docker_user}/netops-demo-py:${TAG_VERSION}"
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