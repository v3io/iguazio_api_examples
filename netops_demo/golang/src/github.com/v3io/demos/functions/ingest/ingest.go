package ingest

import (
	"encoding/json"
	"os"
	"sync"
	"golang.org/x/sync/errgroup"

	"github.com/nuclio/nuclio-sdk-go"
	"github.com/v3io/v3io-go-http"
	"github.com/v3io/v3io-tsdb/pkg/config"
	"github.com/v3io/v3io-tsdb/pkg/tsdb"
	"github.com/v3io/v3io-tsdb/pkg/utils"
)

var adapter *tsdb.V3ioAdapter
var adapterLock sync.Mutex

type metricSamples struct {
	Timestamps []int64                `json:"timestamps,omitempty"`
	Values     []float64              `json:"values,omitempty"`
	Alerts     []string               `json:"alerts,omitempty"`
	IsError    []int                  `json:"is_error,omitempty"`
	Labels     map[string]interface{} `json:"labels,omitempty"`
}

type userData struct {
	tsdbAppender tsdb.Appender
}

func Ingest(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	userData := context.UserData.(*userData)
	parsedMetrics := map[string]*metricSamples{}

	// try to parse the input body
	if err := json.Unmarshal(event.GetBody(), &parsedMetrics); err != nil {
		return nil, nuclio.NewErrBadRequest(err.Error())
	}

	// iterate over metrics
	for metricName, metricSamples := range parsedMetrics {

		// all arrays must contain same # of samples
		if !allMetricSamplesFieldLenEqual(metricSamples) {
			return nil, nuclio.NewErrBadRequest("Expected equal number of samples")
		}

		// iterate over values and ingest them into all time series datastores
		if err := ingestMetricSamples(context, userData.tsdbAppender, metricName, metricSamples); err != nil {
			return nil, nuclio.NewErrBadRequest(err.Error())
		}
	}

	return nil, nil
}

// InitContext runs only once when the function runtime starts
func InitContext(context *nuclio.Context) error {
	context.Logger.InfoWith("Initializing")

	adapterLock.Lock()
	defer adapterLock.Unlock()

	if adapter == nil {
		var err error

		v3ioConfig := config.V3ioConfig{}
		config.InitDefaults(&v3ioConfig)
		v3ioConfig.Path = os.Getenv("V3IO_TSDB_PATH")

		// create adapter once for all contexts
		adapter, err = tsdb.NewV3ioAdapter(&v3ioConfig, context.DataBinding["db0"].(*v3io.Container), context.Logger)
		if err != nil {
			return err
		}
	}

	tsdbAppender, err := adapter.Appender()
	if err != nil {
		return err
	}

	context.UserData = &userData{
		tsdbAppender: tsdbAppender,
	}

	return nil
}

func allMetricSamplesFieldLenEqual(samples *metricSamples) bool {
	return len(samples.Timestamps) == len(samples.Alerts) &&
		len(samples.Timestamps) == len(samples.IsError) &&
		len(samples.Timestamps) == len(samples.Values)
}

func ingestMetricSamples(context *nuclio.Context,
	tsdbAppender tsdb.Appender,
	metricName string,
	samples *metricSamples) error {
	context.Logger.InfoWith("Ingesting",
		"metricName", metricName,
		"samples", len(samples.Timestamps))

	errgroup.Group

	// ingest to TSDB
	if err := ingestMetricSamplesToTSDB(context, tsdbAppender, metricName, samples); err != nil {
		return err
	}

	// ingest to Anodot
	if err := ingestMetricSamplesToTSDB(context, tsdbAppender, metricName, samples); err != nil {
		return err
	}

	return nil
}

func ingestMetricSamplesToTSDB(context *nuclio.Context,
	tsdbAppender tsdb.Appender,
	metricName string,
	samples *metricSamples) error {

	// TODO: can optimize as a pool of utils.Labels with `__name__` already set
	labels := utils.Labels{
		{Name: "__name__", Value: metricName},
	}

	for sampleIndex := 0; sampleIndex < len(samples.Timestamps); sampleIndex++ {

		// shove to appender
		if _, err := tsdbAppender.Add(labels,
			int64(samples.Timestamps[sampleIndex]),
			samples.Values[sampleIndex]); err != nil {
			return err
		}
	}

	return nil
}

func ingestMetricSamplesToAnodot(context *nuclio.Context,
	tsdbAppender tsdb.Appender,
	metricName string,
	samples *metricSamples) error {

	// TODO: can optimize as a pool of utils.Labels with `__name__` already set
	labels := map[string]interface{}{
		"ver":  1,
		"what": metricName,
	}

	for sampleIndex := 0; sampleIndex < len(samples.Timestamps); sampleIndex++ {

		// shove to appender
		if _, err := tsdbAppender.Add(labels,
			int64(samples.Timestamps[sampleIndex]),
			samples.Values[sampleIndex]); err != nil {
			return err
		}
	}

	return nil
}
