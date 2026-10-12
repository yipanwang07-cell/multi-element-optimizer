/** Compatibility for JavaFoil's pre-Java-9 version string test. */
public final class JavaFoilVersionCompat {
    public static String[] versionParts(String version, String separator) {
        String[] parts = version.split(separator);
        String first = parts[0].replaceFirst("[^0-9].*$", "");
        try {
            int major = Integer.parseInt(first);
            if (major >= 2) return new String[] {"1", Integer.toString(major)};
        } catch (NumberFormatException ignored) {
            // Preserve the original behavior for unrecognized version strings.
        }
        return parts;
    }
    public static void main(String[] args) {
        for (String version : new String[] {"1.4.2", "1.5.0", "1.8.0_451", "11", "17.0.20", "21.0.1", "25-ea"}) {
            String[] parts = versionParts(version, "\\.");
            boolean supported = parts.length > 1 && Integer.parseInt(parts[1]) >= 5;
            if (supported != !version.startsWith("1.4")) throw new AssertionError(version);
            System.out.println(version + ": " + (supported ? "supported" : "unsupported"));
        }
    }
}
