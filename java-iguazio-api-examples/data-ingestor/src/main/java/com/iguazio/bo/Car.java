package com.iguazio.bo;

public class Car {

	private long driverId;
	private long timeStamp;
	private double longitude;
	private double latitude;
	private String status;

	public Car(String[] arr) {
		this.driverId = new Long(arr[0]);
		this.timeStamp = new Long(arr[1]);
		this.longitude = new Double(arr[2]);
		this.latitude = new Double(arr[3]);
		this.status = arr[4];

	}

	public long getDriverId() {
		return driverId;
	}

	public void setDriverId(long driverId) {
		this.driverId = driverId;
	}

	public long getTimeStamp() {
		return timeStamp;
	}

	public void setTimeStamp(long timeStamp) {
		this.timeStamp = timeStamp;
	}

	public double getLongitude() {
		return longitude;
	}

	public void setLongitude(double longitude) {
		this.longitude = longitude;
	}

	public double getLatitude() {
		return latitude;
	}

	public void setLatitude(double latitude) {
		this.latitude = latitude;
	}

	public String getStatus() {
		return status;
	}

	public void setStatus(String status) {
		this.status = status;
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + (int) (driverId ^ (driverId >>> 32));
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		Car other = (Car) obj;
		if (driverId != other.driverId)
			return false;
		return true;
	}

	@Override
	public String toString() {
		return driverId + ", " + timeStamp + ", " + longitude + ", " + latitude + ", " + status;
	}

}
