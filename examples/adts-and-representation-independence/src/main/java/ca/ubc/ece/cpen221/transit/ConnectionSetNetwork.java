package ca.ubc.ece.cpen221.transit;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/** Implements TransitNetwork using separate stop and connection sets. */
final class ConnectionSetNetwork implements TransitNetwork {
    private final Set<StopId> stops;
    private final Set<Connection> connections;

    /*
     * Representation invariant:
     * - stops, connections, and their elements are non-null; and
     * - both endpoints of every connection occur in stops.
     * Connection's own specification rules out null endpoints and self-connections.
     *
     * Abstraction function:
     * AF(stops, connections) is the directed graph (V, E) where
     * V = stops and E = { (c.from(), c.to()) | c is in connections }.
     */

    private ConnectionSetNetwork(Set<StopId> stops,
                                 Set<Connection> connections) {
        this.stops = Set.copyOf(Objects.requireNonNull(stops, "stops"));
        this.connections = Set.copyOf(
                Objects.requireNonNull(connections, "connections"));
        checkRep();
    }

    static TransitNetwork empty(Set<StopId> stops) {
        return new ConnectionSetNetwork(stops, Set.of());
    }

    private void checkRep() {
        assert stops != null : "stop set is null";
        assert connections != null : "connection set is null";
        for (StopId stop : stops) {
            assert stop != null : "null stop";
        }
        for (Connection connection : connections) {
            assert connection != null : "null connection";
            assert stops.contains(connection.from())
                    : "connection origin outside the stop set";
            assert stops.contains(connection.to())
                    : "connection destination outside the stop set";
        }
    }

    @Override
    public Set<StopId> stops() {
        return stops;
    }

    @Override
    public boolean contains(StopId stop) {
        return stops.contains(Objects.requireNonNull(stop, "stop"));
    }

    @Override
    public Set<StopId> directDestinationsFrom(StopId stop) {
        requireMember(stop);
        return connections.stream()
                .filter(connection -> connection.from().equals(stop))
                .map(Connection::to)
                .collect(Collectors.toUnmodifiableSet());
    }

    @Override
    public boolean hasDirectConnection(StopId from, StopId to) {
        requireMember(from);
        requireMember(to);
        if (from.equals(to)) {
            return false;
        }
        return connections.contains(new Connection(from, to));
    }

    @Override
    public TransitNetwork withConnection(StopId from, StopId to) {
        requireDistinctMembers(from, to);
        Connection connection = new Connection(from, to);
        if (connections.contains(connection)) {
            return this;
        }

        Set<Connection> updated = new HashSet<>(connections);
        updated.add(connection);
        return new ConnectionSetNetwork(stops, updated);
    }

    private void requireMember(StopId stop) {
        Objects.requireNonNull(stop, "stop");
        if (!stops.contains(stop)) {
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
