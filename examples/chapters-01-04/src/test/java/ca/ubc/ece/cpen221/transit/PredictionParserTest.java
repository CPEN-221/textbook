package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class PredictionParserTest {
    @Test
    void parsesZeroMinutesAtBoundary() throws FeedFormatException {
        ArrivalPrediction prediction = PredictionParser.parse("UBC_EXCHANGE|0");

        assertEquals(new StopId("UBC_EXCHANGE"), prediction.stopId());
        assertEquals(0, prediction.minutesUntilArrival());
    }

    @Test
    void parsesPositiveMinutes() throws FeedFormatException {
        assertEquals(7,
                PredictionParser.parse("UBC_EXCHANGE|7").minutesUntilArrival());
    }

    @Test
    void rejectsMissingMinutes() {
        assertThrows(FeedFormatException.class,
                () -> PredictionParser.parse("UBC_EXCHANGE|"));
    }

    @Test
    void rejectsExtraField() {
        assertThrows(FeedFormatException.class,
                () -> PredictionParser.parse("UBC_EXCHANGE|4|EXTRA"));
    }

    @Test
    void preservesCauseForNonnumericMinutes() {
        FeedFormatException exception = assertThrows(FeedFormatException.class,
                () -> PredictionParser.parse("UBC_EXCHANGE|soon"));

        assertInstanceOf(NumberFormatException.class, exception.getCause());
    }

    @Test
    void rejectsNegativeMinutes() {
        assertThrows(FeedFormatException.class,
                () -> PredictionParser.parse("UBC_EXCHANGE|-1"));
    }

    @Test
    void rejectsBlankStopId() {
        assertThrows(FeedFormatException.class,
                () -> PredictionParser.parse("|4"));
    }

    @Test
    void rejectsNullBeforeParsing() {
        assertThrows(NullPointerException.class,
                () -> PredictionParser.parse(null));
    }
}

