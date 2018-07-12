.PHONY: python-demo
python-demo:
	docker build -f nuclio_python/Dockerfile -t cloud_demo_functions:latest .

.PHONY: push
push:
	docker tag cloud_demo_functions:latest iguaziodocker/cloud_demo_functions:latest
	docker push iguaziodocker/cloud_demo_functions:latest