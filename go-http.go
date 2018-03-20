package main

import (
	"github.com/nuclio/nuclio-sdk-go"
	"github.com/v3io/v3io-go-http"
	"fmt"
)

func GoHTTP(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	container := context.DataBinding["db0"].(*v3io.Container)

	// List Bucket
	ListBucketResponse, ListBucketerr := container.Sync.ListBucket(&v3io.ListBucketInput{
		Path: "/taxi_streaming_example/drivers_table_nuclio/",
	})
	if ListBucketerr != nil {
		context.Logger.ErrorWith("List Bucket *err*", "err", ListBucketerr)
	} else {
		ListBucketOutput := ListBucketResponse.Output.(*v3io.ListBucketOutput)
		context.Logger.InfoWith("List Bucket ", "resp", ListBucketOutput)
	}

	// Put Item
	car := map[string]interface{}{"DriverID": "1", "model": "BMW", "state": "on"}
	PutItemErr := container.Sync.PutItem(&v3io.PutItemInput{
		Path:       "/taxi_streaming_example/drivers/1",
		Attributes: car,
	})
	if PutItemErr != nil {
		context.Logger.ErrorWith("Failed to update item", "err", PutItemErr)
	} else {
		context.Logger.InfoWith("PutItem OK")
	}

	// Put Items
	cars := map[string]map[string]interface{}{
		"2": {"DriverID": "2", "model": "Toyota", "state": "off" },
		"3": {"DriverID": "3", "model": "Jeep", "state": "on" },
		"4": {"DriverID": "3", "model": "Mazda", "state": "on" },
	}
	PutItemsResponse, PutItemsErr := container.Sync.PutItems(&v3io.PutItemsInput{Path:  "/taxi_streaming_example/drivers", Items: cars})
	if PutItemsErr != nil {
		context.Logger.ErrorWith("Put Items *err*", "err", PutItemsErr)
	} else {
		putItemsOutput := PutItemsResponse.Output.(*v3io.PutItemsOutput)
		context.Logger.InfoWith("PutItems ", "resp", putItemsOutput)
	}

	// Get Item
	GetItemResponse, GetItemerr := container.Sync.GetItem(&v3io.GetItemInput{
		Path: "/taxi_streaming_example/drivers_table/980",
		AttributeNames: []string{"*"},})
	if GetItemerr != nil {
		context.Logger.ErrorWith("Get Item *err*", "err", GetItemerr)
	} else {
		GetItemOutput := GetItemResponse.Output.(*v3io.GetItemOutput)
		context.Logger.InfoWith("GetItem ", "resp", GetItemOutput)
	}

	// Get Items
	GetItemsResponse, GetItemserr := container.Sync.GetItems(&v3io.GetItemsInput{
		Path: "/taxi_streaming_example/drivers_table/",
		AttributeNames: []string{"*"},
		Limit: 5,})
	if GetItemserr != nil {
		context.Logger.ErrorWith("Get Item *err*", "err", GetItemserr)
	} else {
		GetItemsOutput := GetItemsResponse.Output.(*v3io.GetItemsOutput)
		context.Logger.InfoWith("GetItems ", "resp", GetItemsOutput)
	}

	// Update Item
	updateExpression := fmt.Sprintf("latitude=51.6")
	UpdateErr := container.Sync.UpdateItem(&v3io.UpdateItemInput{Path: "/taxi_streaming_example/drivers_table/980", Expression: &updateExpression})
	if UpdateErr != nil {
		context.Logger.ErrorWith("Failed to update item", "err", UpdateErr)
	} else {
		context.Logger.InfoWith("UpdateItem OK")
	}

	// Delete Item
	DeleteItemsErr := container.Sync.DeleteObject(&v3io.DeleteObjectInput{Path: "/taxi_streaming_example/drivers/1"})
	if DeleteItemsErr != nil {
		context.Logger.ErrorWith("Delete Items *err*", "err", DeleteItemsErr)
	} else {
		context.Logger.InfoWith("Delete Item OK")
	}

	// Delete Stream
	 DeleteStreamerr := container.Sync.DeleteStream(&v3io.DeleteStreamInput{
		Path:"/taxi_streaming_example/drivers-stream3/",
		})
	if DeleteStreamerr != nil {
		context.Logger.ErrorWith("Delete tream *err*", "err", DeleteStreamerr)
	} else {
		context.Logger.InfoWith("Delete Stream OK")
	}

	// Create Stream
	CreateStreamerr := container.Sync.CreateStream(&v3io.CreateStreamInput{
		Path:"/taxi_streaming_example/drivers-stream3/",
		ShardCount:3,
		RetentionPeriodHours:24,})
	if CreateStreamerr != nil {
		context.Logger.ErrorWith("Create Stream *err*", "err", CreateStreamerr)
	} else {
		context.Logger.InfoWith("Create Stream OK")
	}

	// Put records
	_ , PutRecordserr := container.Sync.PutRecords(&v3io.PutRecordsInput{
		Path: "/taxi_streaming_example/drivers-stream3/",
		Records: []*v3io.StreamRecord{{Data:[]byte("VGhpcyBpcyBteSBtZXNzYWdl") }},
	},)
	if PutRecordserr != nil {
		context.Logger.ErrorWith("Failed to put records in the stream", "err", PutRecordserr)
	} else {
		context.Logger.InfoWith("Put Records OK")
	}

	// Seek Shard
	SeekShardResponse , Seekerr := container.Sync.SeekShard(&v3io.SeekShardInput{
		Path: "/taxi_streaming_example/drivers-stream3/0",
		Type: v3io.SeekShardInputTypeEarliest,
	},)
	if Seekerr != nil {
		context.Logger.ErrorWith("Failed to seek shard in the stream", "err", Seekerr)
	} else {
		SeekShardOutput := SeekShardResponse.Output.(*v3io.SeekShardOutput)
		context.Logger.InfoWith("Seek shard ", "resp", SeekShardOutput)
	}

	// Get Records
	GetRecordsResponse , GetRecordserr := container.Sync.GetRecords(&v3io.GetRecordsInput{
		Path: "/taxi_streaming_example/drivers-stream3/0",
		Location: "AQAAAA0AAAAAAAAAAAAAAA==",
		Limit: 5,
	},)
	if GetRecordserr != nil {
		context.Logger.ErrorWith("Failed to get records from the stream", "err", GetRecordserr)
	} else {
		GetRecordsOutput := GetRecordsResponse.Output.(*v3io.GetRecordsOutput)
		context.Logger.InfoWith("Get records from shard ", "resp", GetRecordsOutput)
	}

	return nil, nil
}