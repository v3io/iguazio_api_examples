/*
Copyright 2017 Iguazio Systems Ltd.

Licensed under the Apache License, Version 2.0 (the "License") with
an addition restriction as set forth herein. You may not use this
file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.

In addition, you may not use the software for any purposes that are
illegal under applicable law, and the grant of the foregoing license
under the Apache 2.0 license is conditioned upon your compliance with
such restriction.
*/
package main

import (
	"bytes"
	"encoding/csv"
	"strconv"

	"github.com/bivas/go-csvhelper"
	"github.com/nuclio/nuclio-sdk-go"
	"github.com/pkg/errors"
	"github.com/v3io/v3io-go-http"
)

type driverEvent struct {
	DriverID  int64
	Timestamp string
	Latitude  string
	Longitude string
	Status     string
}

func DriverEvent(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
    container := context.DataBinding["my_iguazio"].(*v3io.Container)

    reader := csv.NewReader(bytes.NewReader(event.GetBody()))
    dEvent := driverEvent{}
    if err := csvhelper.UnmarshalFieldsByIndex(reader, &dEvent, 0, 1, 2, 3, 4); err != nil {
		return nil, errors.Wrap(err, "Unable to unmarshal event")
	}

    driverId := strconv.FormatInt(dEvent.DriverID, 10)
    timestamp := dEvent.Timestamp
    latitude := dEvent.Latitude
    longitude:= dEvent.Longitude
    status := dEvent.Status

    path := "/taxi_streaming_example/drivers_table_nuclio/driver_"+driverId
   
    PutItemAttributes := make (map[string]interface{})
    PutItemAttributes ["timestamp"]=timestamp
    PutItemAttributes ["lat"]=latitude
    PutItemAttributes ["long"]=longitude
    PutItemAttributes ["status"]=status
    
    PutItemerr := container.Sync.PutItem(&v3io.PutItemInput{
            Path: string(path),
            Attributes: PutItemAttributes})

    if PutItemerr != nil {
            context.Logger.ErrorWith("Put Item *err*", "err", PutItemerr)}

    return nuclio.Response{
        StatusCode:  200,
        ContentType: "application/json",
        Body:        []byte(strconv.FormatInt(dEvent.DriverID, 10))},nil
}
