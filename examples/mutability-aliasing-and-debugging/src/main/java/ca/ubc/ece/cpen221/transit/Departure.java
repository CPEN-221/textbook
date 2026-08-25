package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** An immutable arrival-board departure. */
public record Departure(StopId stopId, String routeName,
                        int minutesUntilArrival) {
    /**
     * Creates a departure.
     *
     * @param stopId the departure stop
     * @param routeName the nonblank passenger-facing route name
     * @param minutesUntilArrival a non-negative wait in minutes
     */
    public Departure {
        Objects.requireNonNull(stopId, "stopId");
        Objects.requireNonNull(routeName, "routeName");
        if (routeName.isBlank()) {
            throw new IllegalArgumentException("route name must not be blank");
        }
        if (minutesUntilArrival < 0) {
            throw new IllegalArgumentException(
                    "minutes until arrival must be non-negative");
        }
    }
}
