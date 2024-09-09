// Code generated by go-swagger; DO NOT EDIT.

package job_service

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"fmt"
	"io"

	"github.com/go-openapi/runtime"

	strfmt "github.com/go-openapi/strfmt"

	job_model "github.com/kubeflow/pipelines/backend/api/v1beta1/go_http_client/job_model"
)

// JobServiceDisableJobReader is a Reader for the JobServiceDisableJob structure.
type JobServiceDisableJobReader struct {
	formats strfmt.Registry
}

// ReadResponse reads a server response into the received o.
func (o *JobServiceDisableJobReader) ReadResponse(response runtime.ClientResponse, consumer runtime.Consumer) (interface{}, error) {
	switch response.Code() {

	case 200:
		result := NewJobServiceDisableJobOK()
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		return result, nil

	default:
		result := NewJobServiceDisableJobDefault(response.Code())
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		if response.Code()/100 == 2 {
			return result, nil
		}
		return nil, result
	}
}

// NewJobServiceDisableJobOK creates a JobServiceDisableJobOK with default headers values
func NewJobServiceDisableJobOK() *JobServiceDisableJobOK {
	return &JobServiceDisableJobOK{}
}

/*JobServiceDisableJobOK handles this case with default header values.

A successful response.
*/
type JobServiceDisableJobOK struct {
	Payload interface{}
}

func (o *JobServiceDisableJobOK) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/jobs/{id}/disable][%d] jobServiceDisableJobOK  %+v", 200, o.Payload)
}

func (o *JobServiceDisableJobOK) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	// response payload
	if err := consumer.Consume(response.Body(), &o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}

// NewJobServiceDisableJobDefault creates a JobServiceDisableJobDefault with default headers values
func NewJobServiceDisableJobDefault(code int) *JobServiceDisableJobDefault {
	return &JobServiceDisableJobDefault{
		_statusCode: code,
	}
}

/*JobServiceDisableJobDefault handles this case with default header values.

An unexpected error response.
*/
type JobServiceDisableJobDefault struct {
	_statusCode int

	Payload *job_model.GatewayruntimeError
}

// Code gets the status code for the job service disable job default response
func (o *JobServiceDisableJobDefault) Code() int {
	return o._statusCode
}

func (o *JobServiceDisableJobDefault) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/jobs/{id}/disable][%d] JobService_DisableJob default  %+v", o._statusCode, o.Payload)
}

func (o *JobServiceDisableJobDefault) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(job_model.GatewayruntimeError)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}
