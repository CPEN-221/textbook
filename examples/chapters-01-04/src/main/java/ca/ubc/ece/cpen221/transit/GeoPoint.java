package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** A WGS84 latitude/longitude pair. */
public record GeoPoint(double latitude, double longitude) {
    /**
     * Creates a geographic point.
     *
     * @param latitude latitude in degrees from -90 through 90
     * @param longitude longitude in degrees from -180 through 180
     */
    public GeoPoint {
        if (!Double.isFinite(latitude) || latitude < -90.0 || latitude > 90.0) {
            throw new IllegalArgumentException("latitude must be in [-90, 90]");
        }
        if (!Double.isFinite(longitude) || longitude < -180.0 || longitude > 180.0) {
            throw new IllegalArgumentException("longitude must be in [-180, 180]");
        }
    }

    /**
     * Computes a simple squared coordinate distance.
     *
     * @param other the other point
     * @return the sum of squared latitude and longitude differences
     * @throws NullPointerException if {@code other} is null
     */
    public double coordinateDistanceSquaredTo(GeoPoint other) {
        Objects.requireNonNull(other, "other");
        double latitudeDifference = latitude - other.latitude;
        double longitudeDifference = longitude - other.longitude;
        return latitudeDifference * latitudeDifference
                + longitudeDifference * longitudeDifference;
    }
}

