package com.iguazio.function;

import java.io.IOException;
import java.util.Properties;
import java.util.concurrent.TimeUnit;

import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.function.VoidFunction;
import org.apache.spark.streaming.v3io.V3IOUtils;
import org.spark_project.guava.primitives.Longs;

import com.iguazio.bo.Car;

import io.iguaz.v3io.daemon.client.api.consts.ConfigProperty;
import io.iguaz.v3io.daemon.client.api.consts.V3IOResultCode.Errors;
import io.iguaz.v3io.streaming.StreamingOperations;
import io.iguaz.v3io.streaming.StreamingOperationsFactory;
import io.iguaz.v3io.streaming.client.api.ProducerRecord;
import io.iguaz.v3io.streaming.client.api.V3IOPutRecordCallback;

public class StreamIngestionVoidFunction implements VoidFunction<JavaRDD<Car>> {

	private static StreamingOperations streamOps;

	public StreamIngestionVoidFunction() {
	}

	public static StreamingOperations getStreamingOperations() throws IOException {

		if (streamOps == null) {
			scala.collection.immutable.HashMap<String, String> hashMap = new scala.collection.immutable.HashMap<>();

			Properties properties = V3IOUtils.toProperties(hashMap);
			properties.setProperty(ConfigProperty.CONTAINER_ID, "1");

			streamOps = StreamingOperationsFactory.create(properties);
			streamOps.createTopic("/cars-stream", (short) 2,
					scala.concurrent.duration.Duration.create(1.0, TimeUnit.HOURS));
		}
		return streamOps;
	}

	@Override
	public void call(JavaRDD<Car> rdd) throws Exception {

		rdd.foreach(new VoidFunction<Car>() {

			@Override
			public void call(Car arg0) throws Exception {
				ProducerRecord rec = new ProducerRecord("/cars-stream", (short) 0, Longs.toByteArray(arg0.getCarId()),
						arg0.toString().getBytes());
				getStreamingOperations().putRecord(rec, new V3IOPutRecordCallback() {

					@Override
					public void onSuccess(long arg0, short arg1) {
						System.out.println("record success");
					}

					@Override
					public void onFailure(Errors arg0) {
						System.out.println("record failed");

					}
				});
			}
		});

	}

}
