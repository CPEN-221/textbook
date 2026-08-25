package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** An immutable transit stop. */
public record Stop(StopId id, String name, GeoPoint location) {
    /**
     * Creates a stop.
     *
     * @param id the stop identifier
     * @param name the nonblank passenger-facing name
     * @param location the stop location
     */
    public Stop {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(location, "location");
        if (name.isBlank()) {
            throw new IllegalArgumentException("stop name must not be blank");
        }
    }
}
