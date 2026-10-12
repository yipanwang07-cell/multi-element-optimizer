import java.nio.file.*;
import org.objectweb.asm.*;
/** Narrow fixes for modern Java detection and the startup age reminder. */
public final class PatchJavaFoil {
    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter writer = new ClassWriter(0);
        boolean age = reader.getClassName().equals("MH/JavaFoil/GlobalSettings");
        if (!age && !reader.getClassName().equals("MH/JavaFoil/OptionsCard"))
            throw new IllegalArgumentException("Unexpected target class");
        final int[] patched = {0};
        reader.accept(new ClassVisitor(Opcodes.ASM7, writer) {
            @Override public MethodVisitor visitMethod(int access, String method, String desc, String signature, String[] exceptions) {
                MethodVisitor delegate = super.visitMethod(access, method, desc, signature, exceptions);
                if (!method.equals(age ? "<init>" : "setSystemInfoTextField")) return delegate;
                return new MethodVisitor(Opcodes.ASM7, delegate) {
                    @Override public void visitMethodInsn(int opcode, String owner, String name, String desc, boolean iface) {
                        if (!age && opcode == Opcodes.INVOKEVIRTUAL && owner.equals("java/lang/String") &&
                            name.equals("split") && desc.equals("(Ljava/lang/String;)[Ljava/lang/String;")) {
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "JavaFoilVersionCompat", "versionParts",
                                "(Ljava/lang/String;Ljava/lang/String;)[Ljava/lang/String;", false);
                            patched[0]++;
                        } else if (age && opcode == Opcodes.INVOKEVIRTUAL && owner.equals("java/util/Calendar") &&
                            name.equals("after") && desc.equals("(Ljava/lang/Object;)Z")) {
                            // Consume both calendars and return false only for the age-reminder condition.
                            // Preserve release metadata, preferences, and all other startup behavior.
                            super.visitInsn(Opcodes.POP2);
                            super.visitInsn(Opcodes.ICONST_0);
                            patched[0]++;
                        } else super.visitMethodInsn(opcode, owner, name, desc, iface);
                    }
                };
            }
        }, 0);
        if (patched[0] != 1) throw new IllegalStateException("Expected one patch site, found " + patched[0]);
        Files.write(Path.of(args[1]), writer.toByteArray());
        System.out.println(age ? "Disabled only the startup age reminder." : "Corrected modern Java version parsing.");
    }
}
