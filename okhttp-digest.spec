Name:		okhttp-digest
Version:	3.1.1
Release:	1
Summary:	Digest authenticator for OkHttp
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/rburgst/okhttp-digest
# Tag 3.1.1. Pure Java, compiled with javac. The only library
# dependency is okhttp 4.12.0.
Source0:	okhttp-digest-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(com.squareup.okhttp3:okhttp)
BuildRequires:	mvn(com.squareup.okio:okio)
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib)
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib-jdk7)
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib-jdk8)

%description
io.github.rburgst:okhttp-digest %{version}. HTTP digest authentication
for com.squareup.okhttp3:okhttp.

%prep
%autosetup -n okhttp-digest-%{version}
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
test "$(find src/main/java -name '*.java' | wc -l)" -eq 25

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
CPOKHTTP=%{_javadir}/okhttp.jar
CPOKIO=%{_javadir}/okio.jar
CPSTD=%{_javadir}/kotlin-stdlib.jar
CPJDK7=%{_javadir}/kotlin-stdlib-jdk7.jar
CPJDK8=%{_javadir}/kotlin-stdlib-jdk8.jar
test -s "$CPOKHTTP"
test -s "$CPOKIO"
test -s "$CPSTD"
test -s "$CPJDK7"
test -s "$CPJDK8"
find src/main/java -name '*.java' > sources.list
test "$(wc -l < sources.list)" -eq 25
mkdir -p classes
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp "$CPOKHTTP:$CPOKIO:$CPSTD:$CPJDK7:$CPJDK8" \
	-d classes @sources.list
test -s classes/com/burgstaller/okhttp/digest/DigestAuthenticator.class
test "$(find classes -name '*.class' | wc -l)" -eq 29
javap -v -classpath classes com.burgstaller.okhttp.digest.DigestAuthenticator | grep -F -q 'major version: 52'
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: com.burgstaller.okhttp' "Implementation-Version: %{version}" > manifest.mf
jar cfm okhttp-digest.jar manifest.mf -C classes .
jar i okhttp-digest.jar
desc=$(jar --describe-module --file okhttp-digest.jar)
printf '%s\n' "$desc"
printf '%s\n' "$desc" | grep -F -q ' com.burgstaller.okhttp'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi

cat > okhttp-digest.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>io.github.rburgst</groupId>
  <artifactId>okhttp-digest</artifactId>
  <version>%{version}</version>
  <name>okhttp-digest</name>
  <description>A digest authenticator for okhttp.</description>
  <url>https://github.com/rburgst/okhttp-digest</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>com.squareup.okhttp3</groupId>
      <artifactId>okhttp</artifactId>
      <version>4.12.0</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact okhttp-digest.pom:okhttp-digest.jar \
	--file-name okhttp-digest \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/io.github.rburgst/okhttp-digest.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "okhttp-digest"' "$idx"
test -s %{buildroot}%{_javadir}/okhttp-digest.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/okhttp-digest.jar
test -s "$JAR"
CP=%{_javadir}/okhttp.jar:%{_javadir}/okio.jar:%{_javadir}/kotlin-stdlib.jar:%{_javadir}/kotlin-stdlib-jdk7.jar:%{_javadir}/kotlin-stdlib-jdk8.jar
mkdir -p check
cat > check/Check.java << 'EOF'
import com.burgstaller.okhttp.digest.Credentials;
import com.burgstaller.okhttp.digest.DigestAuthenticator;
import okhttp3.Protocol;
import okhttp3.Request;
import okhttp3.Response;
import java.nio.charset.StandardCharsets;
import java.util.Random;
public class Check {
	public static void main(String[] args) throws Exception {
		Credentials credentials = new Credentials("user1", "user1");
		DigestAuthenticator auth = new DigestAuthenticator(credentials, StandardCharsets.US_ASCII, new Random(1));
		Request dummy = new Request.Builder().url("http://www.google.com").get().build();
		Response response = new Response.Builder()
			.request(dummy)
			.protocol(Protocol.HTTP_1_1)
			.code(401)
			.message("Unauthorized")
			.header("WWW-Authenticate", "Digest realm=\"myrealm\", nonce=\"BBBBBB\", algorithm=MD5, qop=\"auth\"")
			.build();
		Request authenticated = auth.authenticate(null, response);
		if (authenticated == null) {
			throw new RuntimeException("no request");
		}
		String header = authenticated.header("Authorization");
		if (header == null) {
			throw new RuntimeException("no header");
		}
		System.out.println("okhttp_digest_ok " + header);
	}
}
EOF
javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$JAR:$CP" -d check check/Check.java
java -cp "check:$JAR:$CP" Check > check/out.txt
cat check/out.txt
grep -F -qx 'okhttp_digest_ok Digest username="user1", realm="myrealm", nonce="BBBBBB", uri="/", response="a63e6af31d8af84466d0daf5bd4e3e36", qop=auth, nc=00000001, cnonce="73d51abbd89cb819", algorithm=MD5' check/out.txt

%files -f .mfiles
%license LICENSE.md
%doc NOTICE
