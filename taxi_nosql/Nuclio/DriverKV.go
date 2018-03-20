package main

import (
	"bytes"
	"encoding/csv"
	"strconv"

	"github.com/bivas/go-csvhelper"
	"github.com/nuclio/nuclio-sdk-go"
	"github.com/pkg/errors"
	"github.com/v3io/v3io-go-http"
	"github.com/yaronha/goframe"
)

type driverEvent struct {
	DriverID  int64
	Timestamp string
	Latitude  string
	Longitude string
	Status     string
}

func DriverEvent(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	reader := csv.NewReader(bytes.NewReader(event.GetBody()))
	dEvent := driverEvent{}
	if err := csvhelper.UnmarshalFieldsByIndex(reader, &dEvent, 0, 1, 2, 3, 4); err != nil {
		return nil, errors.Wrap(err, "Unable to unmarshal event")
	}
	cont := context.DataBinding["db1"].(*v3io.Container)

	driverId := strconv.FormatInt(dEvent.DriverID, 10)
	timestamp := dEvent.Timestamp
	latitude := dEvent.Latitude
	longitude:= dEvent.Longitude
	status := dEvent.Status

	df := dataframe.NewDataContext(context.Logger)
	df.Write.ToTable(cont, "/taxi_streaming_example/drivers_table_nuclio/").Keys(driverId).Expression(
		"timestamp='" + timestamp + "';lat='" + latitude + "';long='" + longitude + "';status='" + status + "';").Save()

	return strconv.FormatInt(dEvent.DriverID, 10), nil
}
