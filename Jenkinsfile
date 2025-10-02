pipeline {
  agent {
    docker {
      image 'docker:25.0.3-cli'
      args '-v /var/run/docker.sock:/var/run/docker.sock'
      reuseNode true
    }
  }

  options {
    skipDefaultCheckout(true)
    timestamps()
  }

  environment {
    REPORT_DIR = "security-reports"
    SEMGREP_FAIL_ON = "ERROR"
    TRIVY_FAIL_ON   = "HIGH,CRITICAL"
    JENKINS_CONTAINER = "jenkins"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p "$REPORT_DIR"'
      }
    }

    stage('Semgrep (OWASP)') {
      steps {
        sh '''
          set +e
          docker run --rm \
            --volumes-from "${JENKINS_CONTAINER}" \
            -w "$WORKSPACE" \
            python:3.11-slim bash -lc "
              pip install --no-cache-dir -q semgrep &&
              semgrep \
                --config=p/owasp-top-ten \
                --config=p/python \
                --severity \\"${SEMGREP_FAIL_ON}\\" \
                --sarif --output ${REPORT_DIR}/semgrep.sarif \
                --error
            "
          SEMGREP_RC=$?
          set -e

          [ -f "${REPORT_DIR}/semgrep.sarif" ] || echo '{"version":"2.1.0","runs":[]}' > "${REPORT_DIR}/semgrep.sarif"

          if [ "${SEMGREP_RC:-0}" -ne 0 ]; then
            echo "Semgrep found issues at severity ${SEMGREP_FAIL_ON}."
            exit 1
          fi
        '''
      }
    }

    stage('Bandit (Python SAST)') {
      steps {
        sh '''
          docker run --rm \
            --volumes-from "${JENKINS_CONTAINER}" \
            -w "$WORKSPACE" \
            python:3.11-slim bash -lc "
              pip install --no-cache-dir -q bandit==1.* &&
              bandit -r . -ll -f json -o ${REPORT_DIR}/bandit.json || true
            "
        '''
      }
    }

    stage('pip-audit (Dependencies)') {
      steps {
        sh '''
          REQS=$(ls -1 requirements*.txt 2>/dev/null || true)
          if [ -n "$REQS" ]; then
            docker run --rm \
              --volumes-from "${JENKINS_CONTAINER}" \
              -w "$WORKSPACE" \
              python:3.11-slim bash -lc "
                pip install --no-cache-dir -q pip-audit &&
                for f in ${REQS}; do
                  echo Running pip-audit on $f
                  pip-audit -r $f -f json -o ${REPORT_DIR}/pip-audit_${f%.txt}.json || true
                done
              "
          else
            echo "No requirements*.txt found, skipping pip-audit."
          fi
        '''
      }
    }

    stage('Trivy FS (Secrets & Misconfig)') {
      steps {
        sh '''
          set +e
          docker run --rm \
            --volumes-from "${JENKINS_CONTAINER}" \
            -w "$WORKSPACE" \
            aquasec/trivy:latest fs . \
              --security-checks vuln,secret,config \
              --severity ${TRIVY_FAIL_ON} \
              --format sarif --output ${REPORT_DIR}/trivy.sarif \
              --exit-code 1
          TRIVY_RC=$?
          set -e

          [ -f "${REPORT_DIR}/trivy.sarif" ] || echo '{"version":"2.1.0","runs":[]}' > "${REPORT_DIR}/trivy.sarif"

          if [ "${TRIVY_RC:-0}" -ne 0 ]; then
            echo "Trivy found findings at ${TRIVY_FAIL_ON}."
            exit 1
          fi
        '''
      }
    }

    stage('Publish Reports') {
      steps {
        recordIssues(enabledForFailure: true, tools: [sarif(pattern: "${REPORT_DIR}/*.sarif")])
        archiveArtifacts artifacts: "${REPORT_DIR}/**", allowEmptyArchive: true
      }
    }
  }

  post {
    always  { echo "Scan completed. Reports archived in ${REPORT_DIR}/" }
    failure { echo "Build failed due to security findings. See Warnings and artifacts." }
    success { echo "Build succeeded. No blocking security findings." }
  }
}
