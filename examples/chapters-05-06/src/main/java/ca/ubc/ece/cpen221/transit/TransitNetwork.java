package ca.ubc.ece.cpen221.transit;

import java.util.Set;

/**
 * An immutable finite directed graph whose vertices are transit stops and whose
 * edges are direct connections. A network never contains a connection from a stop
 * to itself.
 */
public interface TransitNetwork {

    /**
     * Creates a network containing exactly {@code stops} and no connections.
     *
     * @param stops the stops to include
     * @return a network containing exactly {@code stops} and no connections
     * @throws NullPointerException if {@code stops} or an element is null
     */
    static TransitNetwork empty(Set<StopId> stops) {
        return AdjacencyMapNetwork.empty(stops);
    }

    /**
     * @return all stops in this network, as an unmodifiable set
     */
    Set<StopId> stops();

    /**
     * Reports whether a stop belongs to this network.
     *
     * @param stop the stop to find
     * @return true exactly when {@code stop} belongs to this network
     * @throws NullPointerException if {@code stop} is null
     */
    boolean contains(StopId stop);

    /**
     * Returns the direct destinations from a stop.
     *
     * @param stop a stop in this network
     * @return the stops {@code to} for which this network contains the direct
     *         connection {@code stop -> to}, as an unmodifiable set
     * @throws NullPointerException if {@code stop} is null
     * @throws IllegalArgumentException if {@code stop} is not in this network
     */
    Set<StopId> directDestinationsFrom(StopId stop);

    /**
     * Reports whether this network contains a direct connection.
     *
     * @param from the connection's origin
     * @param to the connection's destination
     * @return true exactly when this network contains {@code from -> to}
     * @throws NullPointerException if either argument is null
     * @throws IllegalArgumentException if either argument is not in this network
     */
    boolean hasDirectConnection(StopId from, StopId to);

    /**
     * Produces a network with one direct connection included.
     *
     * @param from the connection's origin
     * @param to the connection's destination
     * @return an immutable network with the same stops and connections as this
     *         network, plus {@code from -> to}
     * @throws NullPointerException if either argument is null
     * @throws IllegalArgumentException if either argument is not in this network,
     *         or if the two arguments are equal
     */
    TransitNetwork withConnection(StopId from, StopId to);
}

