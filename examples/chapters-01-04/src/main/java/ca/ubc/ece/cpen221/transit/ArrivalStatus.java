package ca.ubc.ece.cpen221.transit;

/** Classifies an arrival prediction relative to its schedule. */
public final class ArrivalStatus {
    private ArrivalStatus() { }

    /**
     * Describes an arrival prediction.
     *
     * @param scheduledMinute the scheduled minute on the service-day timeline
     * @param predictedMinute the predicted minute on the same timeline
     * @return {@code "EARLY"}, {@code "ON TIME"}, or {@code "LATE"} according to
     *         whether the prediction is before, equal to, or after the schedule
     */
    public static String describe(int scheduledMinute, int predictedMinute) {
        if (predictedMinute < scheduledMinute) {
            return "EARLY";
        }
        if (predictedMinute > scheduledMinute) {
            return "LATE";
        }
        return "ON TIME";
    }
}
