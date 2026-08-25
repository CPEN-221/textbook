package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** A directed connection between two distinct stops. */
record Connection(StopId from, StopId to) {
    Connection {
        Objects.requireNonNull(from, "from");
        Objects.requireNonNull(to, "to");
        if (from.equals(to)) {
            throw new IllegalArgumentException("a direct connection needs two stops");
        }
    }
}

