package ca.ubc.ece.cpen221.transit;

import java.util.Set;

/** A small observation program for the two chapter implementations. */
public final class NetworkDemo {
    private NetworkDemo() {
    }

    public static void main(String[] args) {
        StopId ubc = new StopId("UBC");
        StopId wesbrook = new StopId("WESBROOK");
        TransitNetwork original = TransitNetwork.empty(Set.of(ubc, wesbrook));
        TransitNetwork extended = original.withConnection(ubc, wesbrook);

        System.out.println("original has UBC -> WESBROOK: "
                + original.hasDirectConnection(ubc, wesbrook));
        System.out.println("extended has UBC -> WESBROOK: "
                + extended.hasDirectConnection(ubc, wesbrook));
        System.out.println("extended destinations from UBC: "
                + extended.directDestinationsFrom(ubc));
    }
}

