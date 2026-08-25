package ca.ubc.ece.cpen221.transit;

public final class AllDemos {
    private AllDemos() { }

    public static void main(String[] args) throws Exception {
        EqualityDemo.main(args);
        DelegationDemo.main(args);
        RecursiveJourneyDemo.main(args);
        StreamDemo.main(args);
        ProtocolDemo.main(args);
        VirtualThreadsDemo.main(args);
        ThreadSafetyDemo.main(args);
    }
}
