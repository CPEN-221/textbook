package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** Identifies one transit stop. */
public record StopId(String value) {
    public StopId {
        Objects.requireNonNull(value, "value");
        if (value.isBlank()) {
            throw new IllegalArgumentException("stop id must not be blank");
        }
    }
}
