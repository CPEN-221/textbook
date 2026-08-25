package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** A prediction for one stop. */
public record ArrivalPrediction(StopId stopId, int minutesUntilArrival) {
    /**
     * Creates a prediction.
     *
     * @param stopId the predicted stop
     * @param minutesUntilArrival a non-negative wait in minutes
     */
    public ArrivalPrediction {
        Objects.requireNonNull(stopId, "stopId");
        if (minutesUntilArrival < 0) {
            throw new IllegalArgumentException(
                    "minutes until arrival must be non-negative");
        }
    }
}

