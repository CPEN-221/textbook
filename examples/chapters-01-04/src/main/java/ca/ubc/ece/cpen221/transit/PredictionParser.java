package ca.ubc.ece.cpen221.transit;

import java.util.Objects;

/** Parses the chapter's small text format for arrival predictions. */
public final class PredictionParser {
    private PredictionParser() { }

    /**
     * Parses {@code stop-id|minutes-until-arrival}.
     *
     * @param line one prediction line
     * @return a prediction with a nonblank stop id and non-negative minutes
     * @throws NullPointerException if {@code line} is null
     * @throws FeedFormatException if the line does not contain exactly two fields,
     *         the stop id is blank, or the minutes field is not a non-negative integer
     */
    public static ArrivalPrediction parse(String line) throws FeedFormatException {
        Objects.requireNonNull(line, "line");
        String[] fields = line.split("\\|", -1);
        if (fields.length != 2) {
            throw new FeedFormatException("expected stop-id|minutes: " + line);
        }

        try {
            StopId stopId = new StopId(fields[0]);
            int minutes = Integer.parseInt(fields[1]);
            return new ArrivalPrediction(stopId, minutes);
        } catch (IllegalArgumentException exception) {
            throw new FeedFormatException("invalid prediction: " + line, exception);
        }
    }
}

