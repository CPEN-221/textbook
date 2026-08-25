public final class FrameDemo {
    public static void main(String[] args) {
        int answer = twicePlusOne(20);
        System.out.println(answer);
    }

    static int twicePlusOne(int value) {
        int doubled = twice(value);
        return doubled + 1;
    }

    static int twice(int value) {
        return value * 2;
    }
}
