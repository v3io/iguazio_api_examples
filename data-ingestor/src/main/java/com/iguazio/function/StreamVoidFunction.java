package com.iguazio.function;

import java.util.Iterator;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.function.VoidFunction;

public class StreamVoidFunction implements VoidFunction<JavaRDD<ConsumerRecord<String, String>>> {

	@Override
	public void call(JavaRDD<ConsumerRecord<String, String>> arg0) throws Exception {
		arg0.foreachPartition(new VoidFunction<Iterator<ConsumerRecord<String, String>>>() {

			@Override
			public void call(Iterator<ConsumerRecord<String, String>> arg0) throws Exception {

				while (arg0.hasNext()) {
					ConsumerRecord<String, String> record = arg0.next();
					System.out.println("msg is " + record.value());
				}
			}
		});
	}

}
