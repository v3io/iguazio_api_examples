package ingest

import (
	"encoding/json"
	"os"
	"sync"
	"fmt"
	"golang.org/x/sync/errgroup"

	"github.com/v3io/demos/functions/ingest/anodot"

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

type emitter struct {
	Labels map[string]interface{} `json:"labels,omitempty"`
	Metrics map[string]*metricSamples `json:"metrics,omitempty"`
}

type userData struct {
	tsdbAppender tsdb.Appender
	anodotAppender *anodot.Appender
}

func Ingest(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	userData := context.UserData.(*userData)
	emitters := map[string]*emitter{}

	// try to parse the input body
	if err := json.Unmarshal(event.GetBody(), &emitters); err != nil {
		return nil, nuclio.NewErrBadRequest(err.Error())
	}

	// iterate over emitters
	for _, emitterInfo := range emitters {
		for metricName, metricSamples := range emitterInfo.Metrics {

			// all arrays must contain same # of samples
			if !allMetricSamplesFieldLenEqual(metricSamples) {
				return nil, nuclio.NewErrBadRequest("Expected equal number of samples")
			}

			// iterate over values and ingest them into all time series datastores
			if err := ingestMetricSamples(context, userData, emitterInfo.Labels, metricName, metricSamples); err != nil {
				return nil, nuclio.NewErrBadRequest(err.Error())
			}
		}
	}


	return nil, nil
}

// InitContext runs only once when the function runtime starts
func InitContext(context *nuclio.Context) error {
	var err error
	var userData userData

	// get configuration from env
	tsdbAppenderPath := os.Getenv("INGEST_V3IO_TSDB_PATH")
	anodotAppenderURL := os.Getenv("INGEST_ANODOT_URL")
	anodotAppenderToken := os.Getenv("INGEST_ANODOT_TOKEN")

	context.Logger.InfoWith("Initializing",
		"tsdbAppenderPath", tsdbAppenderPath,
		"anodotAppenderURL", anodotAppenderURL,
		"anodotAppenderToken", anodotAppenderToken)

	// create TSDB appender if path passed in configuration
	if tsdbAppenderPath != "" {
		userData.tsdbAppender, err = createTSDBAppender(context, tsdbAppenderPath)
		if err != nil {
			return err
		}
	}

	// create Anodot appender if token passed in configuration
	if anodotAppenderToken != "" {
		userData.anodotAppender, err = createAnodotAppender(context,
			anodotAppenderURL,
			anodotAppenderToken)
		if err != nil {
			return err
		}
	}

	// set user data into the context
	context.UserData = &userData

	return nil
}

func createTSDBAppender(context *nuclio.Context, path string) (tsdb.Appender, error) {
	context.Logger.InfoWith("Creating TSDB appender", "path", path)

	adapterLock.Lock()
	defer adapterLock.Unlock()

	if adapter == nil {
		var err error

		v3ioConfig := config.V3ioConfig{}
		config.InitDefaults(&v3ioConfig)
		v3ioConfig.Path = path

		// create adapter once for all contexts
		adapter, err = tsdb.NewV3ioAdapter(&v3ioConfig, context.DataBinding["db0"].(*v3io.Container), context.Logger)
		if err != nil {
			return nil, err
		}
	}

	tsdbAppender, err := adapter.Appender()
	if err != nil {
		return nil, err
	}

	return tsdbAppender, nil
}

func createAnodotAppender(context *nuclio.Context, url string, token string) (*anodot.Appender, error) {
	context.Logger.InfoWith("Creating Anodot appender", "url", url, "token", token)

	return anodot.NewAppender(context.Logger, url, token)
}

func allMetricSamplesFieldLenEqual(samples *metricSamples) bool {
	return len(samples.Timestamps) == len(samples.Alerts) &&
		len(samples.Timestamps) == len(samples.IsError) &&
		len(samples.Timestamps) == len(samples.Values)
}

func ingestMetricSamples(context *nuclio.Context,
	userData *userData,
	emitterLabels map[string]interface{},
	metricName string,
	samples *metricSamples) error {
	context.Logger.InfoWith("Ingesting",
		"emitterLabels", emitterLabels,
		"metricName", metricName,
		"numSamples", len(samples.Timestamps))

	var ingestErrGroup errgroup.Group

	// ingest into TSDB if configured to
	if userData.tsdbAppender != nil {
		ingestErrGroup.Go(func() error {
			return ingestMetricSamplesToTSDB(context, userData.tsdbAppender, emitterLabels, metricName, samples)
		})
	}

	// ingest into Anodot
	if userData.anodotAppender != nil {
		ingestErrGroup.Go(func() error {
			return ingestMetricSamplesToAnodot(context, userData.anodotAppender, emitterLabels, metricName, samples)
		})
	}

	// wait and return composite error
	return ingestErrGroup.Wait()
}

func ingestMetricSamplesToTSDB(context *nuclio.Context,
	tsdbAppender tsdb.Appender,
	emitterLabels map[string]interface{},
	metricName string,
	samples *metricSamples) error {

	labels := utils.Labels{
		{Name: "__name__", Value: metricName},
	}

	// labels = emitter labels + metric labels + __name__ for
	for _, labelSource := range []map[string]interface{}{emitterLabels, samples.Labels} {

		// iterate over label source and copy over
		for labelKey, labelValue := range labelSource {
			labels = append(labels, utils.Label{
				Name: labelKey,
				Value: fmt.Sprintf("%v", labelValue),
			})
		}
	}

	// TODO: can optimize as a pool of utils.Labels with `__name__` already set
	for sampleIndex := 0; sampleIndex < len(samples.Timestamps); sampleIndex++ {
		timestamp := int64(samples.Timestamps[sampleIndex]) * 1000

		context.Logger.InfoWith("Ingesting sample to TSDB",
			"timestamp", timestamp,
			"labels", labels,
			"value", samples.Values[sampleIndex])

		// shove to appender
		if _, err := tsdbAppender.Add(labels,
			timestamp,
			samples.Values[sampleIndex]); err != nil {
			return err
		}
	}

	return nil
}

func ingestMetricSamplesToAnodot(context *nuclio.Context,
	anodotAppender *anodot.Appender,
	emitterLabels map[string]interface{},
	metricName string,
	samples *metricSamples) error {

	// add name as "what"
	samples.Labels["what"] = metricName

	var metrics []*anodot.Metric

	for sampleIndex := 0; sampleIndex < len(samples.Timestamps); sampleIndex++ {
		metrics = append(metrics, &anodot.Metric{
			Properties: samples.Labels,
			Timestamp: uint64(samples.Timestamps[sampleIndex]),
			Value: samples.Values[sampleIndex],
		})
	}

	return anodotAppender.Append(metrics)
}
