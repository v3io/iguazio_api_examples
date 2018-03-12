package com.iguazio.function;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.spark.api.java.function.Function;

import com.iguazio.bo.Car;

public class StreamCarFunction implements Function<ConsumerRecord<String, String>, Car> {

	@Override
	public Car call(ConsumerRecord<String, String> arg0) throws Exception {
		return new Car(arg0.value().split(","));
	}

}
