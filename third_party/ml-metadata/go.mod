module github.com/kubeflow/pipelines/third_party/ml-metadata

go 1.21

require (
<<<<<<< HEAD
	google.golang.org/grpc v1.56.3
	google.golang.org/protobuf v1.30.0
)

replace (
	github.com/mattn/go-sqlite3 => github.com/mattn/go-sqlite3 v1.14.18
	golang.org/x/net => golang.org/x/net v0.17.0
=======
	google.golang.org/grpc v1.43.0
	google.golang.org/protobuf v1.27.1
)

require (
	github.com/golang/protobuf v1.5.2 // indirect
	golang.org/x/net v0.0.0-20211216030914-fe4d6282115f // indirect
	golang.org/x/sys v0.0.0-20211216021012-1d35b9e2eb4e // indirect
	golang.org/x/text v0.3.7 // indirect
	google.golang.org/genproto v0.0.0-20211221231510-d629cc9a93d5 // indirect
>>>>>>> upstream-kubeflow-pipelines/master
)
