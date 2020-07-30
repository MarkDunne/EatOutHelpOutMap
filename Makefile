image_name = gcr.io/workspace-160817/eat-out-map

build:
	docker build -t $(image_name) .


push: build
	docker push $(image_name)

run:
	uvicorn main:app --reload