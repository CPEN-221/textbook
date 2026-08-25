package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ArrivalStatusTest {
    @Test
    void classifiesEarlyArrival() {
        assertEquals("EARLY", ArrivalStatus.describe(600, 593));
    }

    @Test
    void classifiesOnTimeArrival() {
        assertEquals("ON TIME", ArrivalStatus.describe(600, 600));
    }

    @Test
    void classifiesLateArrival() {
        assertEquals("LATE", ArrivalStatus.describe(600, 602));
    }

    @Test
    void comparesExtremeIntegersWithoutOverflow() {
        assertEquals("LATE",
                ArrivalStatus.describe(Integer.MIN_VALUE, Integer.MAX_VALUE));
    }
}
