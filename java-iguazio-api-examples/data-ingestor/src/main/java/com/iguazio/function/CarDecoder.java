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
package com.iguazio.function;

import java.nio.charset.Charset;
import java.util.Properties;

import com.iguazio.bo.Car;

import io.iguaz.v3io.spark.streaming.Decoder;
import scala.Function1;
import scala.Option;

public class CarDecoder implements Decoder<Car> {

	@Override
	public Charset encoding(Option<Properties> arg0) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public Option<Properties> encoding$default$1() {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public Car fromBytes(byte[] arg0, Function1<Option<Properties>, Charset> arg1) {
		return new Car(new String(arg0).split(","));
	}

}
