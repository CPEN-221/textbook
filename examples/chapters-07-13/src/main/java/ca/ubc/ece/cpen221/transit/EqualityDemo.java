package ca.ubc.ece.cpen221.transit;

import java.time.Instant;
import java.util.HashMap;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public final class EqualityDemo {
    private EqualityDemo() { }

    public static final Comparator<JourneyOption> BY_ARRIVAL =
            Comparator.comparing(JourneyOption::arrival);

    public static final Comparator<JourneyOption> DISPLAY_ORDER =
            Comparator.comparing(JourneyOption::arrival)
                    .thenComparing(JourneyOption::departure)
                    .thenComparing(JourneyOption::origin)
                    .thenComparing(JourneyOption::destination)
                    .thenComparing(JourneyOption::displayLabel);

    public record JourneyOption(
            String origin,
            String destination,
            Instant departure,
            Instant arrival,
            boolean stepFree,
            String displayLabel) {

        public JourneyOption {
            Objects.requireNonNull(origin);
            Objects.requireNonNull(destination);
            Objects.requireNonNull(departure);
            Objects.requireNonNull(arrival);
            Objects.requireNonNull(displayLabel);
            if (arrival.isBefore(departure)) {
                throw new IllegalArgumentException("arrival precedes departure");
            }
        }
    }

    public static JourneyOption fastest(List<JourneyOption> options) {
        if (options.isEmpty()) {
            throw new IllegalArgumentException("no journey options");
        }
        return options.stream()
                .min(java.util.Comparator.comparing(JourneyOption::arrival))
                .orElseThrow();
    }

    public static String demonstrateMapLookup() {
        Instant departure = Instant.parse("2026-09-08T15:00:00Z");
        JourneyOption stored = new JourneyOption(
                "UBC", "WATERFRONT", departure, departure.plusSeconds(2400),
                true, "R4 then Canada Line");
        JourneyOption query = new JourneyOption(
                "UBC", "WATERFRONT", departure, departure.plusSeconds(2400),
                true, "R4 then Canada Line");

        Map<JourneyOption, Integer> reliability = new HashMap<>();
        reliability.put(stored, 94);
        return "equal=" + stored.equals(query)
                + ", reliability=" + reliability.get(query);
    }

    public static void main(String[] args) {
        System.out.println(demonstrateMapLookup());
    }
}
