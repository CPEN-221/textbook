package ca.ubc.ece.cpen221.transit;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Implements TransitNetwork using a map from each stop to its destinations. */
final class AdjacencyMapNetwork implements TransitNetwork {
    private final Map<StopId, Set<StopId>> outgoing;

    /*
     * Representation invariant:
     * - outgoing, every key, and every destination set and element are non-null;
     * - every destination is also a key in outgoing; and
     * - no stop occurs in its own destination set.
     *
     * Abstraction function:
     * AF(outgoing) is the directed graph (V, E) where
     * V = outgoing.keySet() and
     * E = { (from, to) | to is in outgoing.get(from) }.
     */

    private AdjacencyMapNetwork(Map<StopId, Set<StopId>> outgoing) {
        Objects.requireNonNull(outgoing, "outgoing");
        Map<StopId, Set<StopId>> snapshot = new HashMap<>();
        outgoing.forEach((stop, destinations) ->
                snapshot.put(Objects.requireNonNull(stop, "stop"),
                        Set.copyOf(Objects.requireNonNull(
                                destinations, "destinations"))));
        this.outgoing = Map.copyOf(snapshot);
        checkRep();
    }

    static TransitNetwork empty(Set<StopId> stops) {
        Objects.requireNonNull(stops, "stops");
        Map<StopId, Set<StopId>> outgoing = new HashMap<>();
        for (StopId stop : stops) {
            outgoing.put(Objects.requireNonNull(stop, "stop"), Set.of());
        }
        return new AdjacencyMapNetwork(outgoing);
    }

    private void checkRep() {
        assert outgoing != null : "outgoing map is null";
        for (Map.Entry<StopId, Set<StopId>> entry : outgoing.entrySet()) {
            StopId from = entry.getKey();
            Set<StopId> destinations = entry.getValue();
            assert from != null : "null origin";
            assert destinations != null : "null destination set";
            for (StopId destination : destinations) {
                assert destination != null : "null destination";
            }
            assert outgoing.keySet().containsAll(destinations)
                    : "destination outside the stop set";
            assert !destinations.contains(from) : "self connection";
        }
    }

    @Override
    public Set<StopId> stops() {
        return outgoing.keySet();
    }

    @Override
    public boolean contains(StopId stop) {
        return outgoing.containsKey(Objects.requireNonNull(stop, "stop"));
    }

    @Override
    public Set<StopId> directDestinationsFrom(StopId stop) {
        requireMember(stop);
        return outgoing.get(stop);
    }

    @Override
    public boolean hasDirectConnection(StopId from, StopId to) {
        requireMember(from);
        requireMember(to);
        return outgoing.get(from).contains(to);
    }

    @Override
    public TransitNetwork withConnection(StopId from, StopId to) {
        requireDistinctMembers(from, to);
        if (outgoing.get(from).contains(to)) {
            return this;
        }

        Map<StopId, Set<StopId>> updated = new HashMap<>(outgoing);
        Set<StopId> destinations = new HashSet<>(outgoing.get(from));
        destinations.add(to);
        updated.put(from, Set.copyOf(destinations));
        return new AdjacencyMapNetwork(updated);
    }

    private void requireMember(StopId stop) {
        Objects.requireNonNull(stop, "stop");
        if (!outgoing.containsKey(stop)) {
            throw new IllegalArgumentException("stop is not in the network: " + stop);
        }
    }

    private void requireDistinctMembers(StopId from, StopId to) {
        requireMember(from);
        requireMember(to);
        if (from.equals(to)) {
            throw new IllegalArgumentException("a direct connection needs two stops");
        }
    }
}
