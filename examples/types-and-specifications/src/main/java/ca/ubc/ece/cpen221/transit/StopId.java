package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** A persistent identifier for a transit stop. */
public record StopId(String value) {
    /**
     * Creates a stop identifier.
     *
     * @param value the nonblank identifier text
     * @throws NullPointerException if {@code value} is null
     * @throws IllegalArgumentException if {@code value} is blank
     */
    public StopId {
        Objects.requireNonNull(value, "value");
        if (value.isBlank()) {
            throw new IllegalArgumentException("stop id must not be blank");
        }
    }
}
