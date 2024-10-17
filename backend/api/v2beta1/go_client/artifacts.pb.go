// Copyright 2024 The Kubeflow Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Code generated by protoc-gen-go. DO NOT EDIT.
// versions:
// 	protoc-gen-go v1.33.0
// 	protoc        v3.17.3
// source: backend/api/v2beta1/artifacts.proto

package go_client

import (
	context "context"
	_ "google.golang.org/genproto/googleapis/api/annotations"
	_ "google.golang.org/genproto/googleapis/api/httpbody"
	status "google.golang.org/genproto/googleapis/rpc/status"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status1 "google.golang.org/grpc/status"
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	timestamppb "google.golang.org/protobuf/types/known/timestamppb"
	reflect "reflect"
	sync "sync"
)

const (
	// Verify that this generated code is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	// Verify that runtime/protoimpl is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

type GetArtifactRequest_ArtifactView int32

const (
	// Not specified, equivalent to BASIC.
	GetArtifactRequest_ARTIFACT_VIEW_UNSPECIFIED GetArtifactRequest_ArtifactView = 0
	// Server responses excludes download_url
	GetArtifactRequest_BASIC GetArtifactRequest_ArtifactView = 1
	// Server responses include download_url
	GetArtifactRequest_DOWNLOAD GetArtifactRequest_ArtifactView = 2
)

// Enum value maps for GetArtifactRequest_ArtifactView.
var (
	GetArtifactRequest_ArtifactView_name = map[int32]string{
		0: "ARTIFACT_VIEW_UNSPECIFIED",
		1: "BASIC",
		2: "DOWNLOAD",
	}
	GetArtifactRequest_ArtifactView_value = map[string]int32{
		"ARTIFACT_VIEW_UNSPECIFIED": 0,
		"BASIC":                     1,
		"DOWNLOAD":                  2,
	}
)

func (x GetArtifactRequest_ArtifactView) Enum() *GetArtifactRequest_ArtifactView {
	p := new(GetArtifactRequest_ArtifactView)
	*p = x
	return p
}

func (x GetArtifactRequest_ArtifactView) String() string {
	return protoimpl.X.EnumStringOf(x.Descriptor(), protoreflect.EnumNumber(x))
}

func (GetArtifactRequest_ArtifactView) Descriptor() protoreflect.EnumDescriptor {
	return file_backend_api_v2beta1_artifacts_proto_enumTypes[0].Descriptor()
}

func (GetArtifactRequest_ArtifactView) Type() protoreflect.EnumType {
	return &file_backend_api_v2beta1_artifacts_proto_enumTypes[0]
}

func (x GetArtifactRequest_ArtifactView) Number() protoreflect.EnumNumber {
	return protoreflect.EnumNumber(x)
}

// Deprecated: Use GetArtifactRequest_ArtifactView.Descriptor instead.
func (GetArtifactRequest_ArtifactView) EnumDescriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{0, 0}
}

type ListArtifactRequest_Field int32

const (
	ListArtifactRequest_FIELD_UNSPECIFIED ListArtifactRequest_Field = 0
	ListArtifactRequest_CREATE_TIME       ListArtifactRequest_Field = 1
	ListArtifactRequest_LAST_UPDATE_TIME  ListArtifactRequest_Field = 2
	ListArtifactRequest_ID                ListArtifactRequest_Field = 3
)

// Enum value maps for ListArtifactRequest_Field.
var (
	ListArtifactRequest_Field_name = map[int32]string{
		0: "FIELD_UNSPECIFIED",
		1: "CREATE_TIME",
		2: "LAST_UPDATE_TIME",
		3: "ID",
	}
	ListArtifactRequest_Field_value = map[string]int32{
		"FIELD_UNSPECIFIED": 0,
		"CREATE_TIME":       1,
		"LAST_UPDATE_TIME":  2,
		"ID":                3,
	}
)

func (x ListArtifactRequest_Field) Enum() *ListArtifactRequest_Field {
	p := new(ListArtifactRequest_Field)
	*p = x
	return p
}

func (x ListArtifactRequest_Field) String() string {
	return protoimpl.X.EnumStringOf(x.Descriptor(), protoreflect.EnumNumber(x))
}

func (ListArtifactRequest_Field) Descriptor() protoreflect.EnumDescriptor {
	return file_backend_api_v2beta1_artifacts_proto_enumTypes[1].Descriptor()
}

func (ListArtifactRequest_Field) Type() protoreflect.EnumType {
	return &file_backend_api_v2beta1_artifacts_proto_enumTypes[1]
}

func (x ListArtifactRequest_Field) Number() protoreflect.EnumNumber {
	return protoreflect.EnumNumber(x)
}

// Deprecated: Use ListArtifactRequest_Field.Descriptor instead.
func (ListArtifactRequest_Field) EnumDescriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{1, 0}
}

type GetArtifactRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// Required. The ID of the artifact to be retrieved.
	ArtifactId string `protobuf:"bytes,1,opt,name=artifact_id,json=artifactId,proto3" json:"artifact_id,omitempty"`
	// Optional. Set to "DOWNLOAD" to included a signed URL with
	// an expiry (default 15 seconds, unless configured other wise).
	// This URL can be used to download the Artifact directly from
	// the Artifact's storage provider. Set to "BASIC" to exclude
	// the download_url from server responses, thus preventing the
	// creation of any signed url.
	// Defaults to BASIC.
	View GetArtifactRequest_ArtifactView `protobuf:"varint,2,opt,name=view,proto3,enum=kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest_ArtifactView" json:"view,omitempty"`
}

func (x *GetArtifactRequest) Reset() {
	*x = GetArtifactRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[0]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *GetArtifactRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*GetArtifactRequest) ProtoMessage() {}

func (x *GetArtifactRequest) ProtoReflect() protoreflect.Message {
	mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[0]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use GetArtifactRequest.ProtoReflect.Descriptor instead.
func (*GetArtifactRequest) Descriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{0}
}

func (x *GetArtifactRequest) GetArtifactId() string {
	if x != nil {
		return x.ArtifactId
	}
	return ""
}

func (x *GetArtifactRequest) GetView() GetArtifactRequest_ArtifactView {
	if x != nil {
		return x.View
	}
	return GetArtifactRequest_ARTIFACT_VIEW_UNSPECIFIED
}

// Passed onto MLMD ListOperationOptions
// https://github.com/kubeflow/pipelines/blob/master/third_party/ml-metadata/ml_metadata/proto/metadata_store.proto#L868
type ListArtifactRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// Optional.
	// Max number of resources to return in the result. A value of zero or less
	// will result in the default (20).
	// The API implementation also enforces an upper-bound of 100, and picks the
	// minimum between this value and the one specified here.
	// [default = 20]
	MaxResultSize int32 `protobuf:"varint,1,opt,name=max_result_size,json=maxResultSize,proto3" json:"max_result_size,omitempty"`
	// Optional. Ordering field. [default = ID]
	OrderByField ListArtifactRequest_Field `protobuf:"varint,2,opt,name=order_by_field,json=orderByField,proto3,enum=kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest_Field" json:"order_by_field,omitempty"`
	// Optional. Can be either "asc" (ascending) or "desc" (descending). [default = asc]
	OrderBy string `protobuf:"bytes,3,opt,name=order_by,json=orderBy,proto3" json:"order_by,omitempty"`
	// Optional. The next_page_token value returned from a previous List request, if any.
	NextPageToken string `protobuf:"bytes,4,opt,name=next_page_token,json=nextPageToken,proto3" json:"next_page_token,omitempty"`
	// Required. Namespace of the Artifact's context.
	Namespace string `protobuf:"bytes,5,opt,name=namespace,proto3" json:"namespace,omitempty"`
}

func (x *ListArtifactRequest) Reset() {
	*x = ListArtifactRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[1]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ListArtifactRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ListArtifactRequest) ProtoMessage() {}

func (x *ListArtifactRequest) ProtoReflect() protoreflect.Message {
	mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[1]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ListArtifactRequest.ProtoReflect.Descriptor instead.
func (*ListArtifactRequest) Descriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{1}
}

func (x *ListArtifactRequest) GetMaxResultSize() int32 {
	if x != nil {
		return x.MaxResultSize
	}
	return 0
}

func (x *ListArtifactRequest) GetOrderByField() ListArtifactRequest_Field {
	if x != nil {
		return x.OrderByField
	}
	return ListArtifactRequest_FIELD_UNSPECIFIED
}

func (x *ListArtifactRequest) GetOrderBy() string {
	if x != nil {
		return x.OrderBy
	}
	return ""
}

func (x *ListArtifactRequest) GetNextPageToken() string {
	if x != nil {
		return x.NextPageToken
	}
	return ""
}

func (x *ListArtifactRequest) GetNamespace() string {
	if x != nil {
		return x.Namespace
	}
	return ""
}

type ListArtifactResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// List of retrieved artifacts.
	Artifacts []*Artifact `protobuf:"bytes,1,rep,name=artifacts,proto3" json:"artifacts,omitempty"`
	// Token to retrieve the next page of results, or empty if there are none
	NextPageToken string `protobuf:"bytes,2,opt,name=next_page_token,json=nextPageToken,proto3" json:"next_page_token,omitempty"`
}

func (x *ListArtifactResponse) Reset() {
	*x = ListArtifactResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[2]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ListArtifactResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ListArtifactResponse) ProtoMessage() {}

func (x *ListArtifactResponse) ProtoReflect() protoreflect.Message {
	mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[2]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ListArtifactResponse.ProtoReflect.Descriptor instead.
func (*ListArtifactResponse) Descriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{2}
}

func (x *ListArtifactResponse) GetArtifacts() []*Artifact {
	if x != nil {
		return x.Artifacts
	}
	return nil
}

func (x *ListArtifactResponse) GetNextPageToken() string {
	if x != nil {
		return x.NextPageToken
	}
	return ""
}

type Artifact struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// Unique Artifact ID. Generated by MLMD.
	ArtifactId string `protobuf:"bytes,1,opt,name=artifact_id,json=artifactId,proto3" json:"artifact_id,omitempty"`
	// Storage Provider to which this Artifact is located (e.g. S3, Minio, etc.).
	StorageProvider string `protobuf:"bytes,2,opt,name=storage_provider,json=storageProvider,proto3" json:"storage_provider,omitempty"`
	// The path location of this Artifact within the storage provider.
	// For example an object located at s3://my-bucket/path/a/b/c will
	// result in "path/a/b/c".
	StoragePath string `protobuf:"bytes,3,opt,name=storage_path,json=storagePath,proto3" json:"storage_path,omitempty"`
	// The Artifact URI
	Uri string `protobuf:"bytes,4,opt,name=uri,proto3" json:"uri,omitempty"`
	// Optional Output. Specifies a signed-url that can be used to
	// download this Artifact directly from its store.
	DownloadUrl string `protobuf:"bytes,5,opt,name=download_url,json=downloadUrl,proto3" json:"download_url,omitempty"`
	// The namespace associated with this Artifact. This is determined
	// by the namespace of the parent PipelineRun that created this Artifact.
	Namespace string `protobuf:"bytes,6,opt,name=namespace,proto3" json:"namespace,omitempty"`
	// The MLMD type of the artifact (e.g. system.Dataset)
	ArtifactType string `protobuf:"bytes,7,opt,name=artifact_type,json=artifactType,proto3" json:"artifact_type,omitempty"`
	// The size of the artifact in bytes.
	// If the artifact does not exist in object store (e.g. Metrics)
	// then this is omitted.
	ArtifactSize int64 `protobuf:"varint,8,opt,name=artifact_size,json=artifactSize,proto3" json:"artifact_size,omitempty"`
	// Creation time of the artifact.
	CreatedAt *timestamppb.Timestamp `protobuf:"bytes,9,opt,name=created_at,json=createdAt,proto3" json:"created_at,omitempty"`
	// Last update time of the artifact.
	LastUpdatedAt *timestamppb.Timestamp `protobuf:"bytes,10,opt,name=last_updated_at,json=lastUpdatedAt,proto3" json:"last_updated_at,omitempty"`
	// In case any error happens retrieving an artifact field, only artifact ID
	// and the error message is returned. Client has the flexibility of choosing
	// how to handle the error. This is especially useful when calling ListArtifacts.
	Error *status.Status `protobuf:"bytes,11,opt,name=error,proto3" json:"error,omitempty"`
}

func (x *Artifact) Reset() {
	*x = Artifact{}
	if protoimpl.UnsafeEnabled {
		mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[3]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *Artifact) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*Artifact) ProtoMessage() {}

func (x *Artifact) ProtoReflect() protoreflect.Message {
	mi := &file_backend_api_v2beta1_artifacts_proto_msgTypes[3]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use Artifact.ProtoReflect.Descriptor instead.
func (*Artifact) Descriptor() ([]byte, []int) {
	return file_backend_api_v2beta1_artifacts_proto_rawDescGZIP(), []int{3}
}

func (x *Artifact) GetArtifactId() string {
	if x != nil {
		return x.ArtifactId
	}
	return ""
}

func (x *Artifact) GetStorageProvider() string {
	if x != nil {
		return x.StorageProvider
	}
	return ""
}

func (x *Artifact) GetStoragePath() string {
	if x != nil {
		return x.StoragePath
	}
	return ""
}

func (x *Artifact) GetUri() string {
	if x != nil {
		return x.Uri
	}
	return ""
}

func (x *Artifact) GetDownloadUrl() string {
	if x != nil {
		return x.DownloadUrl
	}
	return ""
}

func (x *Artifact) GetNamespace() string {
	if x != nil {
		return x.Namespace
	}
	return ""
}

func (x *Artifact) GetArtifactType() string {
	if x != nil {
		return x.ArtifactType
	}
	return ""
}

func (x *Artifact) GetArtifactSize() int64 {
	if x != nil {
		return x.ArtifactSize
	}
	return 0
}

func (x *Artifact) GetCreatedAt() *timestamppb.Timestamp {
	if x != nil {
		return x.CreatedAt
	}
	return nil
}

func (x *Artifact) GetLastUpdatedAt() *timestamppb.Timestamp {
	if x != nil {
		return x.LastUpdatedAt
	}
	return nil
}

func (x *Artifact) GetError() *status.Status {
	if x != nil {
		return x.Error
	}
	return nil
}

var File_backend_api_v2beta1_artifacts_proto protoreflect.FileDescriptor

var file_backend_api_v2beta1_artifacts_proto_rawDesc = []byte{
	0x0a, 0x23, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e, 0x64, 0x2f, 0x61, 0x70, 0x69, 0x2f, 0x76, 0x32,
	0x62, 0x65, 0x74, 0x61, 0x31, 0x2f, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x2e,
	0x70, 0x72, 0x6f, 0x74, 0x6f, 0x12, 0x26, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2e,
	0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e,
	0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x1a, 0x1c, 0x67,
	0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2f, 0x61, 0x70, 0x69, 0x2f, 0x61, 0x6e, 0x6e, 0x6f, 0x74, 0x61,
	0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x1a, 0x19, 0x67, 0x6f, 0x6f,
	0x67, 0x6c, 0x65, 0x2f, 0x61, 0x70, 0x69, 0x2f, 0x68, 0x74, 0x74, 0x70, 0x62, 0x6f, 0x64, 0x79,
	0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x1a, 0x17, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2f, 0x72,
	0x70, 0x63, 0x2f, 0x73, 0x74, 0x61, 0x74, 0x75, 0x73, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x1a,
	0x1f, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2f, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x62, 0x75, 0x66,
	0x2f, 0x74, 0x69, 0x6d, 0x65, 0x73, 0x74, 0x61, 0x6d, 0x70, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f,
	0x22, 0xda, 0x01, 0x0a, 0x12, 0x47, 0x65, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74,
	0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x1f, 0x0a, 0x0b, 0x61, 0x72, 0x74, 0x69, 0x66,
	0x61, 0x63, 0x74, 0x5f, 0x69, 0x64, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0a, 0x61, 0x72,
	0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x49, 0x64, 0x12, 0x5b, 0x0a, 0x04, 0x76, 0x69, 0x65, 0x77,
	0x18, 0x02, 0x20, 0x01, 0x28, 0x0e, 0x32, 0x47, 0x2e, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f,
	0x77, 0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b,
	0x65, 0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x2e,
	0x47, 0x65, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x52, 0x65, 0x71, 0x75, 0x65,
	0x73, 0x74, 0x2e, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x56, 0x69, 0x65, 0x77, 0x52,
	0x04, 0x76, 0x69, 0x65, 0x77, 0x22, 0x46, 0x0a, 0x0c, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63,
	0x74, 0x56, 0x69, 0x65, 0x77, 0x12, 0x1d, 0x0a, 0x19, 0x41, 0x52, 0x54, 0x49, 0x46, 0x41, 0x43,
	0x54, 0x5f, 0x56, 0x49, 0x45, 0x57, 0x5f, 0x55, 0x4e, 0x53, 0x50, 0x45, 0x43, 0x49, 0x46, 0x49,
	0x45, 0x44, 0x10, 0x00, 0x12, 0x09, 0x0a, 0x05, 0x42, 0x41, 0x53, 0x49, 0x43, 0x10, 0x01, 0x12,
	0x0c, 0x0a, 0x08, 0x44, 0x4f, 0x57, 0x4e, 0x4c, 0x4f, 0x41, 0x44, 0x10, 0x02, 0x22, 0xd6, 0x02,
	0x0a, 0x13, 0x4c, 0x69, 0x73, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x52, 0x65,
	0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x26, 0x0a, 0x0f, 0x6d, 0x61, 0x78, 0x5f, 0x72, 0x65, 0x73,
	0x75, 0x6c, 0x74, 0x5f, 0x73, 0x69, 0x7a, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x0d,
	0x6d, 0x61, 0x78, 0x52, 0x65, 0x73, 0x75, 0x6c, 0x74, 0x53, 0x69, 0x7a, 0x65, 0x12, 0x67, 0x0a,
	0x0e, 0x6f, 0x72, 0x64, 0x65, 0x72, 0x5f, 0x62, 0x79, 0x5f, 0x66, 0x69, 0x65, 0x6c, 0x64, 0x18,
	0x02, 0x20, 0x01, 0x28, 0x0e, 0x32, 0x41, 0x2e, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77,
	0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65,
	0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x2e, 0x4c,
	0x69, 0x73, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x52, 0x65, 0x71, 0x75, 0x65,
	0x73, 0x74, 0x2e, 0x46, 0x69, 0x65, 0x6c, 0x64, 0x52, 0x0c, 0x6f, 0x72, 0x64, 0x65, 0x72, 0x42,
	0x79, 0x46, 0x69, 0x65, 0x6c, 0x64, 0x12, 0x19, 0x0a, 0x08, 0x6f, 0x72, 0x64, 0x65, 0x72, 0x5f,
	0x62, 0x79, 0x18, 0x03, 0x20, 0x01, 0x28, 0x09, 0x52, 0x07, 0x6f, 0x72, 0x64, 0x65, 0x72, 0x42,
	0x79, 0x12, 0x26, 0x0a, 0x0f, 0x6e, 0x65, 0x78, 0x74, 0x5f, 0x70, 0x61, 0x67, 0x65, 0x5f, 0x74,
	0x6f, 0x6b, 0x65, 0x6e, 0x18, 0x04, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0d, 0x6e, 0x65, 0x78, 0x74,
	0x50, 0x61, 0x67, 0x65, 0x54, 0x6f, 0x6b, 0x65, 0x6e, 0x12, 0x1c, 0x0a, 0x09, 0x6e, 0x61, 0x6d,
	0x65, 0x73, 0x70, 0x61, 0x63, 0x65, 0x18, 0x05, 0x20, 0x01, 0x28, 0x09, 0x52, 0x09, 0x6e, 0x61,
	0x6d, 0x65, 0x73, 0x70, 0x61, 0x63, 0x65, 0x22, 0x4d, 0x0a, 0x05, 0x46, 0x69, 0x65, 0x6c, 0x64,
	0x12, 0x15, 0x0a, 0x11, 0x46, 0x49, 0x45, 0x4c, 0x44, 0x5f, 0x55, 0x4e, 0x53, 0x50, 0x45, 0x43,
	0x49, 0x46, 0x49, 0x45, 0x44, 0x10, 0x00, 0x12, 0x0f, 0x0a, 0x0b, 0x43, 0x52, 0x45, 0x41, 0x54,
	0x45, 0x5f, 0x54, 0x49, 0x4d, 0x45, 0x10, 0x01, 0x12, 0x14, 0x0a, 0x10, 0x4c, 0x41, 0x53, 0x54,
	0x5f, 0x55, 0x50, 0x44, 0x41, 0x54, 0x45, 0x5f, 0x54, 0x49, 0x4d, 0x45, 0x10, 0x02, 0x12, 0x06,
	0x0a, 0x02, 0x49, 0x44, 0x10, 0x03, 0x22, 0x8e, 0x01, 0x0a, 0x14, 0x4c, 0x69, 0x73, 0x74, 0x41,
	0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x12,
	0x4e, 0x0a, 0x09, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x18, 0x01, 0x20, 0x03,
	0x28, 0x0b, 0x32, 0x30, 0x2e, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2e, 0x70, 0x69,
	0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e, 0x64, 0x2e,
	0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x2e, 0x41, 0x72, 0x74, 0x69,
	0x66, 0x61, 0x63, 0x74, 0x52, 0x09, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x12,
	0x26, 0x0a, 0x0f, 0x6e, 0x65, 0x78, 0x74, 0x5f, 0x70, 0x61, 0x67, 0x65, 0x5f, 0x74, 0x6f, 0x6b,
	0x65, 0x6e, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0d, 0x6e, 0x65, 0x78, 0x74, 0x50, 0x61,
	0x67, 0x65, 0x54, 0x6f, 0x6b, 0x65, 0x6e, 0x22, 0xbf, 0x03, 0x0a, 0x08, 0x41, 0x72, 0x74, 0x69,
	0x66, 0x61, 0x63, 0x74, 0x12, 0x1f, 0x0a, 0x0b, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74,
	0x5f, 0x69, 0x64, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0a, 0x61, 0x72, 0x74, 0x69, 0x66,
	0x61, 0x63, 0x74, 0x49, 0x64, 0x12, 0x29, 0x0a, 0x10, 0x73, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65,
	0x5f, 0x70, 0x72, 0x6f, 0x76, 0x69, 0x64, 0x65, 0x72, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52,
	0x0f, 0x73, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x50, 0x72, 0x6f, 0x76, 0x69, 0x64, 0x65, 0x72,
	0x12, 0x21, 0x0a, 0x0c, 0x73, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x5f, 0x70, 0x61, 0x74, 0x68,
	0x18, 0x03, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0b, 0x73, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x50,
	0x61, 0x74, 0x68, 0x12, 0x10, 0x0a, 0x03, 0x75, 0x72, 0x69, 0x18, 0x04, 0x20, 0x01, 0x28, 0x09,
	0x52, 0x03, 0x75, 0x72, 0x69, 0x12, 0x21, 0x0a, 0x0c, 0x64, 0x6f, 0x77, 0x6e, 0x6c, 0x6f, 0x61,
	0x64, 0x5f, 0x75, 0x72, 0x6c, 0x18, 0x05, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0b, 0x64, 0x6f, 0x77,
	0x6e, 0x6c, 0x6f, 0x61, 0x64, 0x55, 0x72, 0x6c, 0x12, 0x1c, 0x0a, 0x09, 0x6e, 0x61, 0x6d, 0x65,
	0x73, 0x70, 0x61, 0x63, 0x65, 0x18, 0x06, 0x20, 0x01, 0x28, 0x09, 0x52, 0x09, 0x6e, 0x61, 0x6d,
	0x65, 0x73, 0x70, 0x61, 0x63, 0x65, 0x12, 0x23, 0x0a, 0x0d, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61,
	0x63, 0x74, 0x5f, 0x74, 0x79, 0x70, 0x65, 0x18, 0x07, 0x20, 0x01, 0x28, 0x09, 0x52, 0x0c, 0x61,
	0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x54, 0x79, 0x70, 0x65, 0x12, 0x23, 0x0a, 0x0d, 0x61,
	0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x5f, 0x73, 0x69, 0x7a, 0x65, 0x18, 0x08, 0x20, 0x01,
	0x28, 0x03, 0x52, 0x0c, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x53, 0x69, 0x7a, 0x65,
	0x12, 0x39, 0x0a, 0x0a, 0x63, 0x72, 0x65, 0x61, 0x74, 0x65, 0x64, 0x5f, 0x61, 0x74, 0x18, 0x09,
	0x20, 0x01, 0x28, 0x0b, 0x32, 0x1a, 0x2e, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2e, 0x70, 0x72,
	0x6f, 0x74, 0x6f, 0x62, 0x75, 0x66, 0x2e, 0x54, 0x69, 0x6d, 0x65, 0x73, 0x74, 0x61, 0x6d, 0x70,
	0x52, 0x09, 0x63, 0x72, 0x65, 0x61, 0x74, 0x65, 0x64, 0x41, 0x74, 0x12, 0x42, 0x0a, 0x0f, 0x6c,
	0x61, 0x73, 0x74, 0x5f, 0x75, 0x70, 0x64, 0x61, 0x74, 0x65, 0x64, 0x5f, 0x61, 0x74, 0x18, 0x0a,
	0x20, 0x01, 0x28, 0x0b, 0x32, 0x1a, 0x2e, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2e, 0x70, 0x72,
	0x6f, 0x74, 0x6f, 0x62, 0x75, 0x66, 0x2e, 0x54, 0x69, 0x6d, 0x65, 0x73, 0x74, 0x61, 0x6d, 0x70,
	0x52, 0x0d, 0x6c, 0x61, 0x73, 0x74, 0x55, 0x70, 0x64, 0x61, 0x74, 0x65, 0x64, 0x41, 0x74, 0x12,
	0x28, 0x0a, 0x05, 0x65, 0x72, 0x72, 0x6f, 0x72, 0x18, 0x0b, 0x20, 0x01, 0x28, 0x0b, 0x32, 0x12,
	0x2e, 0x67, 0x6f, 0x6f, 0x67, 0x6c, 0x65, 0x2e, 0x72, 0x70, 0x63, 0x2e, 0x53, 0x74, 0x61, 0x74,
	0x75, 0x73, 0x52, 0x05, 0x65, 0x72, 0x72, 0x6f, 0x72, 0x32, 0xec, 0x02, 0x0a, 0x0f, 0x41, 0x72,
	0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x53, 0x65, 0x72, 0x76, 0x69, 0x63, 0x65, 0x12, 0xab, 0x01,
	0x0a, 0x0d, 0x4c, 0x69, 0x73, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x12,
	0x3b, 0x2e, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c,
	0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69,
	0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x2e, 0x4c, 0x69, 0x73, 0x74, 0x41, 0x72, 0x74,
	0x69, 0x66, 0x61, 0x63, 0x74, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x3c, 0x2e, 0x6b,
	0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65,
	0x73, 0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32,
	0x62, 0x65, 0x74, 0x61, 0x31, 0x2e, 0x4c, 0x69, 0x73, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61,
	0x63, 0x74, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x22, 0x1f, 0x82, 0xd3, 0xe4, 0x93,
	0x02, 0x19, 0x12, 0x17, 0x2f, 0x61, 0x70, 0x69, 0x73, 0x2f, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61,
	0x31, 0x2f, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x12, 0xaa, 0x01, 0x0a, 0x0b,
	0x47, 0x65, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x12, 0x3a, 0x2e, 0x6b, 0x75,
	0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73,
	0x2e, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62,
	0x65, 0x74, 0x61, 0x31, 0x2e, 0x47, 0x65, 0x74, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74,
	0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x30, 0x2e, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c,
	0x6f, 0x77, 0x2e, 0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2e, 0x62, 0x61, 0x63,
	0x6b, 0x65, 0x6e, 0x64, 0x2e, 0x61, 0x70, 0x69, 0x2e, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31,
	0x2e, 0x41, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x22, 0x2d, 0x82, 0xd3, 0xe4, 0x93, 0x02,
	0x27, 0x12, 0x25, 0x2f, 0x61, 0x70, 0x69, 0x73, 0x2f, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31,
	0x2f, 0x61, 0x72, 0x74, 0x69, 0x66, 0x61, 0x63, 0x74, 0x73, 0x2f, 0x7b, 0x61, 0x72, 0x74, 0x69,
	0x66, 0x61, 0x63, 0x74, 0x5f, 0x69, 0x64, 0x7d, 0x42, 0x3d, 0x5a, 0x3b, 0x67, 0x69, 0x74, 0x68,
	0x75, 0x62, 0x2e, 0x63, 0x6f, 0x6d, 0x2f, 0x6b, 0x75, 0x62, 0x65, 0x66, 0x6c, 0x6f, 0x77, 0x2f,
	0x70, 0x69, 0x70, 0x65, 0x6c, 0x69, 0x6e, 0x65, 0x73, 0x2f, 0x62, 0x61, 0x63, 0x6b, 0x65, 0x6e,
	0x64, 0x2f, 0x61, 0x70, 0x69, 0x2f, 0x76, 0x32, 0x62, 0x65, 0x74, 0x61, 0x31, 0x2f, 0x67, 0x6f,
	0x5f, 0x63, 0x6c, 0x69, 0x65, 0x6e, 0x74, 0x62, 0x06, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x33,
}

var (
	file_backend_api_v2beta1_artifacts_proto_rawDescOnce sync.Once
	file_backend_api_v2beta1_artifacts_proto_rawDescData = file_backend_api_v2beta1_artifacts_proto_rawDesc
)

func file_backend_api_v2beta1_artifacts_proto_rawDescGZIP() []byte {
	file_backend_api_v2beta1_artifacts_proto_rawDescOnce.Do(func() {
		file_backend_api_v2beta1_artifacts_proto_rawDescData = protoimpl.X.CompressGZIP(file_backend_api_v2beta1_artifacts_proto_rawDescData)
	})
	return file_backend_api_v2beta1_artifacts_proto_rawDescData
}

var file_backend_api_v2beta1_artifacts_proto_enumTypes = make([]protoimpl.EnumInfo, 2)
var file_backend_api_v2beta1_artifacts_proto_msgTypes = make([]protoimpl.MessageInfo, 4)
var file_backend_api_v2beta1_artifacts_proto_goTypes = []interface{}{
	(GetArtifactRequest_ArtifactView)(0), // 0: kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest.ArtifactView
	(ListArtifactRequest_Field)(0),       // 1: kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest.Field
	(*GetArtifactRequest)(nil),           // 2: kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest
	(*ListArtifactRequest)(nil),          // 3: kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest
	(*ListArtifactResponse)(nil),         // 4: kubeflow.pipelines.backend.api.v2beta1.ListArtifactResponse
	(*Artifact)(nil),                     // 5: kubeflow.pipelines.backend.api.v2beta1.Artifact
	(*timestamppb.Timestamp)(nil),        // 6: google.protobuf.Timestamp
	(*status.Status)(nil),                // 7: google.rpc.Status
}
var file_backend_api_v2beta1_artifacts_proto_depIdxs = []int32{
	0, // 0: kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest.view:type_name -> kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest.ArtifactView
	1, // 1: kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest.order_by_field:type_name -> kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest.Field
	5, // 2: kubeflow.pipelines.backend.api.v2beta1.ListArtifactResponse.artifacts:type_name -> kubeflow.pipelines.backend.api.v2beta1.Artifact
	6, // 3: kubeflow.pipelines.backend.api.v2beta1.Artifact.created_at:type_name -> google.protobuf.Timestamp
	6, // 4: kubeflow.pipelines.backend.api.v2beta1.Artifact.last_updated_at:type_name -> google.protobuf.Timestamp
	7, // 5: kubeflow.pipelines.backend.api.v2beta1.Artifact.error:type_name -> google.rpc.Status
	3, // 6: kubeflow.pipelines.backend.api.v2beta1.ArtifactService.ListArtifacts:input_type -> kubeflow.pipelines.backend.api.v2beta1.ListArtifactRequest
	2, // 7: kubeflow.pipelines.backend.api.v2beta1.ArtifactService.GetArtifact:input_type -> kubeflow.pipelines.backend.api.v2beta1.GetArtifactRequest
	4, // 8: kubeflow.pipelines.backend.api.v2beta1.ArtifactService.ListArtifacts:output_type -> kubeflow.pipelines.backend.api.v2beta1.ListArtifactResponse
	5, // 9: kubeflow.pipelines.backend.api.v2beta1.ArtifactService.GetArtifact:output_type -> kubeflow.pipelines.backend.api.v2beta1.Artifact
	8, // [8:10] is the sub-list for method output_type
	6, // [6:8] is the sub-list for method input_type
	6, // [6:6] is the sub-list for extension type_name
	6, // [6:6] is the sub-list for extension extendee
	0, // [0:6] is the sub-list for field type_name
}

func init() { file_backend_api_v2beta1_artifacts_proto_init() }
func file_backend_api_v2beta1_artifacts_proto_init() {
	if File_backend_api_v2beta1_artifacts_proto != nil {
		return
	}
	if !protoimpl.UnsafeEnabled {
		file_backend_api_v2beta1_artifacts_proto_msgTypes[0].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*GetArtifactRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_backend_api_v2beta1_artifacts_proto_msgTypes[1].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ListArtifactRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_backend_api_v2beta1_artifacts_proto_msgTypes[2].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ListArtifactResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_backend_api_v2beta1_artifacts_proto_msgTypes[3].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*Artifact); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_backend_api_v2beta1_artifacts_proto_rawDesc,
			NumEnums:      2,
			NumMessages:   4,
			NumExtensions: 0,
			NumServices:   1,
		},
		GoTypes:           file_backend_api_v2beta1_artifacts_proto_goTypes,
		DependencyIndexes: file_backend_api_v2beta1_artifacts_proto_depIdxs,
		EnumInfos:         file_backend_api_v2beta1_artifacts_proto_enumTypes,
		MessageInfos:      file_backend_api_v2beta1_artifacts_proto_msgTypes,
	}.Build()
	File_backend_api_v2beta1_artifacts_proto = out.File
	file_backend_api_v2beta1_artifacts_proto_rawDesc = nil
	file_backend_api_v2beta1_artifacts_proto_goTypes = nil
	file_backend_api_v2beta1_artifacts_proto_depIdxs = nil
}

// Reference imports to suppress errors if they are not otherwise used.
var _ context.Context
var _ grpc.ClientConnInterface

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
const _ = grpc.SupportPackageIsVersion6

// ArtifactServiceClient is the client API for ArtifactService service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://godoc.org/google.golang.org/grpc#ClientConn.NewStream.
type ArtifactServiceClient interface {
	// Finds all artifacts within the specified namespace.
	// Namespace field is required. In multi-user mode, the caller
	// is required to have RBAC verb "list" on the "artifacts"
	// resource for the specified namespace.
	ListArtifacts(ctx context.Context, in *ListArtifactRequest, opts ...grpc.CallOption) (*ListArtifactResponse, error)
	// Finds a specific Artifact by ID.
	GetArtifact(ctx context.Context, in *GetArtifactRequest, opts ...grpc.CallOption) (*Artifact, error)
}

type artifactServiceClient struct {
	cc grpc.ClientConnInterface
}

func NewArtifactServiceClient(cc grpc.ClientConnInterface) ArtifactServiceClient {
	return &artifactServiceClient{cc}
}

func (c *artifactServiceClient) ListArtifacts(ctx context.Context, in *ListArtifactRequest, opts ...grpc.CallOption) (*ListArtifactResponse, error) {
	out := new(ListArtifactResponse)
	err := c.cc.Invoke(ctx, "/kubeflow.pipelines.backend.api.v2beta1.ArtifactService/ListArtifacts", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *artifactServiceClient) GetArtifact(ctx context.Context, in *GetArtifactRequest, opts ...grpc.CallOption) (*Artifact, error) {
	out := new(Artifact)
	err := c.cc.Invoke(ctx, "/kubeflow.pipelines.backend.api.v2beta1.ArtifactService/GetArtifact", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ArtifactServiceServer is the server API for ArtifactService service.
type ArtifactServiceServer interface {
	// Finds all artifacts within the specified namespace.
	// Namespace field is required. In multi-user mode, the caller
	// is required to have RBAC verb "list" on the "artifacts"
	// resource for the specified namespace.
	ListArtifacts(context.Context, *ListArtifactRequest) (*ListArtifactResponse, error)
	// Finds a specific Artifact by ID.
	GetArtifact(context.Context, *GetArtifactRequest) (*Artifact, error)
}

// UnimplementedArtifactServiceServer can be embedded to have forward compatible implementations.
type UnimplementedArtifactServiceServer struct {
}

func (*UnimplementedArtifactServiceServer) ListArtifacts(context.Context, *ListArtifactRequest) (*ListArtifactResponse, error) {
	return nil, status1.Errorf(codes.Unimplemented, "method ListArtifacts not implemented")
}
func (*UnimplementedArtifactServiceServer) GetArtifact(context.Context, *GetArtifactRequest) (*Artifact, error) {
	return nil, status1.Errorf(codes.Unimplemented, "method GetArtifact not implemented")
}

func RegisterArtifactServiceServer(s *grpc.Server, srv ArtifactServiceServer) {
	s.RegisterService(&_ArtifactService_serviceDesc, srv)
}

func _ArtifactService_ListArtifacts_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(ListArtifactRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ArtifactServiceServer).ListArtifacts(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/kubeflow.pipelines.backend.api.v2beta1.ArtifactService/ListArtifacts",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(ArtifactServiceServer).ListArtifacts(ctx, req.(*ListArtifactRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _ArtifactService_GetArtifact_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(GetArtifactRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ArtifactServiceServer).GetArtifact(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/kubeflow.pipelines.backend.api.v2beta1.ArtifactService/GetArtifact",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(ArtifactServiceServer).GetArtifact(ctx, req.(*GetArtifactRequest))
	}
	return interceptor(ctx, in, info, handler)
}

var _ArtifactService_serviceDesc = grpc.ServiceDesc{
	ServiceName: "kubeflow.pipelines.backend.api.v2beta1.ArtifactService",
	HandlerType: (*ArtifactServiceServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "ListArtifacts",
			Handler:    _ArtifactService_ListArtifacts_Handler,
		},
		{
			MethodName: "GetArtifact",
			Handler:    _ArtifactService_GetArtifact_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "backend/api/v2beta1/artifacts.proto",
}
