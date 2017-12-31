package main

import (
	"bytes"
	"encoding/csv"
	"strconv"

	"github.com/bivas/go-csvhelper"
	"github.com/nuclio/nuclio-sdk"
	"github.com/pkg/errors"
	"github.com/v3io/v3io-go-http"
	"github.com/yaronha/goframe"
)

type driverEvent struct {
	DriverID  int64
	Latitude  float64
	Longitude float64
	Speed     float64
	Timestamp int64
	CellID    int64
}

func DriverEvent(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	reader := csv.NewReader(bytes.NewReader(event.GetBody()))
	dEvent := driverEvent{}
	if err := csvhelper.UnmarshalFieldsByIndex(reader, &dEvent, 0, 1, 2, 3, 4, 5); err != nil {
		return nil, errors.Wrap(err, "Unable to unmarshal event")
	}
	cont, err := createContainer(context.Logger, "192.168.224.69:8081", "bigdata")
	if err != nil {
		return nil, errors.Wrap(err, "Failed to create container")
	}

	df := dataframe.NewDataContext(context.Logger)
	driverId := strconv.FormatInt(dEvent.DriverID, 10)
	cellId := strconv.FormatInt(dEvent.CellID, 10)
	row := df.Read.FromTable(cont, "drivers").Keys(driverId).Where("exists(current_cell_id)").GetRow()
	changed := "0"
	prevCellIdValue := "0"
	if row == nil {
		df.Write.ToTable(cont, "drivers").Keys(driverId).Expression(
			`current_cell_id=` + cellId + `;previous_cell_id=0;change_cell_id_indicator=1;`).Save()
			changed = "1"
	} else {
		prevCellIdValue := row.Col("previous_cell_id").AsStr()
		if cellId != prevCellIdValue {
			changed = "1"
		}
		df.Write.ToTable(cont, "drivers").Keys(driverId).Expression(
			`previous_cell_id=current_cell_id;current_cell_id=` + cellId + `;change_cell_id_indicator=` + changed + `;`).Save()
	}

	if changed == "1" {
		existingCell := df.Read.FromTable(cont, "cells").Keys(cellId).Where("exists(count").GetRow()
		if existingCell == nil {
			df.Write.ToTable(cont, "cells").Keys(cellId).Expression("count=1").Save()
		} else {
			df.Write.ToTable(cont, "cells").Keys(cellId).Expression("count=count+1").Save()
		}
		if prevCellIdValue != "0" {
			df.Write.ToTable(cont, "cells").Keys(prevCellIdValue).Expression("count=count-1").Save()
		}
	}

	return strconv.FormatInt(dEvent.DriverID, 10), nil
}

func createContainer(logger nuclio.Logger, addr, cont string) (*v3io.Container, error) {
	// create context
	context, err := v3io.NewContext(logger, addr, 8)
	if err != nil {
		return nil, errors.Wrap(err, "Failed to create client")
	}

	// create session
	session, err := context.NewSession("", "", "v3test")
	if err != nil {
		return nil, errors.Wrap(err, "Failed to create session")
	}

	// create the container
	container, err := session.NewContainer(cont)
	if err != nil {
		return nil, errors.Wrap(err, "Failed to create container")
	}

	return container, nil
}
