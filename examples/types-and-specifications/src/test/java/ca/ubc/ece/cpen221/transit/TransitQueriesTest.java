package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import org.junit.jupiter.api.Test;

class TransitQueriesTest {
    private static final Stop EXCHANGE = new Stop(
            new StopId("UBC_EXCHANGE"),
            "UBC Exchange",
            new GeoPoint(49.2675, -123.2477));
    private static final Stop LOOP = new Stop(
            new StopId("UBC_LOOP"),
            "UBC Bus Loop",
            new GeoPoint(49.2660, -123.2490));

    @Test
    void rejectsInvalidLatitude() {
        assertThrows(IllegalArgumentException.class,
                () -> new GeoPoint(-123.249, 49.261));
    }

    @Test
    void choosesNearestStop() {
        assertEquals(EXCHANGE, TransitQueries.nearestStop(
                new GeoPoint(49.2674, -123.2478),
                List.of(LOOP, EXCHANGE)));
    }

    @Test
    void choosesFirstStopWhenDistancesTie() {
        Stop sameLocation = new Stop(
                new StopId("SAME_LOCATION"),
                "Same Location",
                EXCHANGE.location());

        assertEquals(EXCHANGE, TransitQueries.nearestStop(
                EXCHANGE.location(), List.of(EXCHANGE, sameLocation)));
    }

    @Test
    void rejectsEmptyCandidateList() {
        assertThrows(IllegalArgumentException.class,
                () -> TransitQueries.nearestStop(
                        new GeoPoint(49.2674, -123.2478), List.of()));
    }
}
