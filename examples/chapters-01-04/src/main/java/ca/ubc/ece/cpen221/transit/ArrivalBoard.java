package ca.ubc.ece.cpen221.transit;

import java.util.List;
import java.util.Objects;

/** A feed-ordered, immutable snapshot of upcoming departures. */
public final class ArrivalBoard {
    private final List<Departure> departures;

    /**
     * Creates a snapshot in the input collection's iteration order.
     *
     * @param departures non-null departures in feed order
     * @throws NullPointerException if the list or an element is null
     */
    public ArrivalBoard(List<Departure> departures) {
        Objects.requireNonNull(departures, "departures");
        this.departures = List.copyOf(departures);
    }

    /**
     * Returns the upcoming departures.
     *
     * @return an unmodifiable list in feed order
     */
    public List<Departure> upcoming() {
        return departures;
    }
}

