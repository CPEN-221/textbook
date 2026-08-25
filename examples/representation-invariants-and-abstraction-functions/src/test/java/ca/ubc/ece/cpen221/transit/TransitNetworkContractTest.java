package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class TransitNetworkContractTest {
    private static final StopId UBC = new StopId("UBC");
    private static final StopId WESBROOK = new StopId("WESBROOK");
    private static final StopId ALMA = new StopId("ALMA");

    static Stream<Arguments> implementations() {
        return Stream.of(
                Arguments.of("adjacency map",
                        (Function<Set<StopId>, TransitNetwork>)
                                AdjacencyMapNetwork::empty),
                Arguments.of("connection set",
                        (Function<Set<StopId>, TransitNetwork>)
                                ConnectionSetNetwork::empty));
    }

    @ParameterizedTest(name = "{0}: empty factory preserves isolated stops")
    @MethodSource("implementations")
    void emptyFactoryPreservesIsolatedStops(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork network = factory.apply(Set.of(UBC, WESBROOK));

        assertEquals(Set.of(UBC, WESBROOK), network.stops());
        assertTrue(network.directDestinationsFrom(UBC).isEmpty());
    }

    @ParameterizedTest(name = "{0}: producer leaves original unchanged")
    @MethodSource("implementations")
    void producerLeavesOriginalUnchanged(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork original = factory.apply(Set.of(UBC, WESBROOK, ALMA));
        TransitNetwork extended = original.withConnection(UBC, WESBROOK);

        assertFalse(original.hasDirectConnection(UBC, WESBROOK));
        assertTrue(extended.hasDirectConnection(UBC, WESBROOK));
        assertEquals(Set.of(WESBROOK), extended.directDestinationsFrom(UBC));
        assertEquals(Set.of(UBC, WESBROOK, ALMA), extended.stops());
    }

    @ParameterizedTest(name = "{0}: duplicate connection keeps abstract value")
    @MethodSource("implementations")
    void duplicateConnectionKeepsAbstractValue(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork once = factory.apply(Set.of(UBC, WESBROOK))
                .withConnection(UBC, WESBROOK);
        TransitNetwork twice = once.withConnection(UBC, WESBROOK);

        assertEquals(once.stops(), twice.stops());
        assertEquals(once.directDestinationsFrom(UBC),
                twice.directDestinationsFrom(UBC));
    }

    @ParameterizedTest(name = "{0}: results are unmodifiable snapshots")
    @MethodSource("implementations")
    void resultsAreUnmodifiable(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork network = factory.apply(Set.of(UBC, WESBROOK))
                .withConnection(UBC, WESBROOK);

        Set<StopId> destinations = network.directDestinationsFrom(UBC);
        assertThrows(UnsupportedOperationException.class,
                () -> destinations.add(ALMA));
        assertThrows(UnsupportedOperationException.class,
                () -> network.stops().remove(UBC));
    }

    @ParameterizedTest(name = "{0}: factory detaches from mutable input")
    @MethodSource("implementations")
    void factoryDetachesFromMutableInput(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        Set<StopId> supplied = new HashSet<>(Set.of(UBC, WESBROOK));
        TransitNetwork network = factory.apply(supplied);

        supplied.clear();

        assertEquals(Set.of(UBC, WESBROOK), network.stops());
    }

    @ParameterizedTest(name = "{0}: invalid connections are rejected")
    @MethodSource("implementations")
    void invalidConnectionsAreRejected(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork network = factory.apply(Set.of(UBC, WESBROOK));

        assertThrows(IllegalArgumentException.class,
                () -> network.withConnection(UBC, UBC));
        assertThrows(IllegalArgumentException.class,
                () -> network.withConnection(UBC, ALMA));
        assertThrows(NullPointerException.class,
                () -> network.withConnection(null, WESBROOK));
    }

    @ParameterizedTest(name = "{0}: direction matters")
    @MethodSource("implementations")
    void directionMatters(
            String ignoredName,
            Function<Set<StopId>, TransitNetwork> factory) {
        TransitNetwork network = factory.apply(Set.of(UBC, WESBROOK))
                .withConnection(UBC, WESBROOK);

        assertTrue(network.hasDirectConnection(UBC, WESBROOK));
        assertFalse(network.hasDirectConnection(WESBROOK, UBC));
    }

    @Test
    void publicFactoryUsesTheContract() {
        TransitNetwork network = TransitNetwork.empty(Set.of(UBC, WESBROOK));

        assertEquals(Set.of(UBC, WESBROOK), network.stops());
    }
}
