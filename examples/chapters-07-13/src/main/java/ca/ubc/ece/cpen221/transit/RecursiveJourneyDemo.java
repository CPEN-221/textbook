package ca.ubc.ece.cpen221.transit;

public final class RecursiveJourneyDemo {
    private RecursiveJourneyDemo() { }

    public sealed interface Journey permits Arrive, Travel { }

    public record Arrive(String stop) implements Journey { }

    public record Travel(String route, String from, String to,
                         int minutes, Journey rest) implements Journey {
        public Travel {
            if (minutes < 0) {
                throw new IllegalArgumentException("negative duration");
            }
            if (!to.equals(firstStop(rest))) {
                throw new IllegalArgumentException("disconnected journey");
            }
        }
    }

    public static String firstStop(Journey journey) {
        return switch (journey) {
            case Arrive(String stop) -> stop;
            case Travel(String route, String from, String to,
                        int minutes, Journey rest) -> from;
        };
    }

    public static int totalMinutes(Journey journey) {
        return switch (journey) {
            case Arrive(String stop) -> 0;
            case Travel(String route, String from, String to,
                        int minutes, Journey rest) ->
                    minutes + totalMinutes(rest);
        };
    }

    public static int legCount(Journey journey) {
        return switch (journey) {
            case Arrive(String stop) -> 0;
            case Travel(String route, String from, String to,
                        int minutes, Journey rest) -> 1 + legCount(rest);
        };
    }

    public static int totalMinutesIterative(Journey journey) {
        int total = 0;
        Journey current = journey;
        while (current instanceof Travel travel) {
            total = Math.addExact(total, travel.minutes());
            current = travel.rest();
        }
        return total;
    }

    public static void main(String[] args) {
        Journey journey = new Travel("R4", "UBC", "OAKRIDGE", 28,
                new Travel("CANADA_LINE", "OAKRIDGE", "WATERFRONT", 14,
                        new Arrive("WATERFRONT")));
        System.out.println("minutes=" + totalMinutes(journey)
                + ", legs=" + legCount(journey));
    }
}
