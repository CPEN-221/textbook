plugins {
    java
    application
}

group = "ca.ubc.ece.cpen221"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

dependencies {
    testImplementation(platform("org.junit:junit-bom:6.1.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.add("-Xlint:all")
}

tasks.test {
    useJUnitPlatform()
    enableAssertions = true
}

application {
    mainClass = "ca.ubc.ece.cpen221.transit.AllDemos"
}

tasks.named<JavaExec>("run") {
    enableAssertions = true
}

