package ca.ubc.ece.cpen221.transit;

import java.util.List;
import java.util.Objects;

/** Queries over frozen transit data. */
public final class TransitQueries {
    private TransitQueries() { }

    /**
     * Finds the stop nearest to an origin in coordinate space.
     *
     * @param origin the point from which distance is measured
     * @param stops candidate stops, in tie-breaking order
     * @return the first stop in {@code stops} whose squared coordinate distance from
     *         {@code origin} is minimal
     * @throws NullPointerException if {@code origin}, {@code stops}, or an element of
     *         {@code stops} is null
     * @throws IllegalArgumentException if {@code stops} is empty
     */
    public static Stop nearestStop(GeoPoint origin, List<Stop> stops) {
        Objects.requireNonNull(origin, "origin");
        Objects.requireNonNull(stops, "stops");
        if (stops.isEmpty()) {
            throw new IllegalArgumentException("stops must not be empty");
        }

        Stop nearest = Objects.requireNonNull(stops.getFirst(), "stop");
        double nearestDistance = origin.coordinateDistanceSquaredTo(nearest.location());

        for (Stop candidate : stops) {
            Objects.requireNonNull(candidate, "stop");
            double candidateDistance =
                    origin.coordinateDistanceSquaredTo(candidate.location());
            if (candidateDistance < nearestDistance) {
                nearest = candidate;
                nearestDistance = candidateDistance;
            }
        }
        return nearest;
    }
}
