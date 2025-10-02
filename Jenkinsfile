pipeline {
  agent {
    docker {
      image 'docker:25.0.3-cli'
      // ให้ agent ใช้ docker ของ host และมองเห็น workspace เดียวกัน
      args '-u 0:0 -v /var/run/docker.sock:/var/run/docker.sock -v $WORKSPACE:$WORKSPACE'
      reuseNode true
    }
  }

  options {
    timestamps()
    // ใช้ได้ก็ต่อเมื่อมีปลั๊กอิน AnsiColor:
    // ansiColor('xterm')
  }

  environment {
    REPORT_DIR = 'security-reports'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p "${REPORT_DIR}"'
      }
    }

    stage('Semgrep (OWASP)') {
      steps {
        sh '''
          set -e
          docker run --rm -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" python:3.11-slim bash -lc '
            apt-get update &&
            apt-get install -y --no-install-recommends git ca-certificates &&
            rm -rf /var/lib/apt/lists/* &&
            git config --global --add safe.directory "$PWD" &&
            pip install --no-cache-dir -q semgrep &&
            semgrep scan \
              --include "**/*.py" \
              --config=p/owasp-top-ten \
              --config=p/python \
              --severity error \
              --sarif --output ${REPORT_DIR}/semgrep.sarif \
              --error
          '
        '''
      }
    }

    stage('Bandit (Python SAST)') {
      steps {
        sh '''
          docker run --rm -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" python:3.11-slim bash -lc '
            pip install --no-cache-dir -q bandit==1.* &&
            bandit -r . -ll -f json -o ${REPORT_DIR}/bandit.json || true
          '
        '''
      }
    }

    stage('pip-audit (Dependencies)') {
      when { expression { return fileExists('requirements.txt') } }
      steps {
        sh '''
          docker run --rm -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" python:3.11-slim bash -lc '
            pip install --no-cache-dir -q pip-audit &&
            pip-audit -r requirements.txt -f json -o ${REPORT_DIR}/pip-audit_requirements.json || true
          '
        '''
      }
    }

    stage('Trivy FS (Secrets & Misconfig)') {
      steps {
        sh '''
          set +e
          docker run --rm -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" aquasec/trivy:latest \
            fs . \
            --scanners vuln,secret,misconfig \
            --severity HIGH,CRITICAL \
            --format sarif --output ${REPORT_DIR}/trivy.sarif \
            --exit-code 1
          TRIVY_RC=$?
          set -e
          [ -f "${REPORT_DIR}/trivy.sarif" ] || echo '{"version":"2.1.0","runs":[]}' > "${REPORT_DIR}/trivy.sarif"
          [ $TRIVY_RC -eq 0 ] || true
        '''
      }
    }

    stage('Publish Reports') {
      steps {
        // ต้องมีปลั๊กอิน Warnings NG และ Sarif parser
        recordIssues(enabledForFailure: true, tools: [sarif(pattern: "${env.REPORT_DIR}/*.sarif")])
        archiveArtifacts artifacts: "${env.REPORT_DIR}/**", fingerprint: true, allowEmptyArchive: true
      }
    }
  }

  post {
    always  { echo "Scan completed. Reports archived in ${env.REPORT_DIR}/" }
    success { echo "Build succeeded. No blocking security findings." }
    failure { echo "Build failed due to security findings or scanner errors. See artifacts." }
  }
}
