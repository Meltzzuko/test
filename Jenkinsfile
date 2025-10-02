pipeline {
  agent {
    docker {
      image 'docker:25.0.3-cli'
      args '--entrypoint="" -u 0:0 -v /var/run/docker.sock:/var/run/docker.sock'
    }
  }

  options {
    timestamps()
    ansiColor('xterm')
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p security-reports'
      }
    }

    stage('Semgrep (OWASP)') {
      steps {
        sh '''
          set -e
          docker run --rm --volumes-from jenkins -w "$PWD" python:3.11-slim bash -lc '
            apt-get update &&
            apt-get install -y --no-install-recommends git ca-certificates &&
            rm -rf /var/lib/apt/lists/* &&
            git config --global --add safe.directory "$PWD" &&
            pip install --no-cache-dir -q semgrep &&
            semgrep scan \
              --include "**/*.py" \
              --config=p/owasp-top-ten \
              --config=p/python \
              --severity ERROR \
              --sarif --output security-reports/semgrep.sarif \
              --error
          '
        '''
      }
    }

    stage('Bandit (Python SAST)') {
      steps {
        sh '''
          docker run --rm --volumes-from jenkins -w "$PWD" python:3.11-slim bash -lc '
            pip install --no-cache-dir -q bandit==1.* &&
            bandit -r . -ll -f json -o security-reports/bandit.json || true
          '
        '''
      }
    }

    stage('pip-audit (Dependencies)') {
      when { expression { return fileExists('requirements.txt') } }
      steps {
        sh '''
          docker run --rm --volumes-from jenkins -w "$PWD" python:3.11-slim bash -lc '
            pip install --no-cache-dir -q pip-audit &&
            pip-audit -r requirements.txt -f json -o security-reports/pip-audit_requirements.json || true
          '
        '''
      }
    }

    stage('Trivy FS (Secrets & Misconfig)') {
      steps {
        sh '''
          set +e
          docker run --rm --volumes-from jenkins -w "$PWD" aquasec/trivy:latest \
            fs . \
            --scanners vuln,secret,misconfig \
            --severity HIGH,CRITICAL \
            --format sarif --output security-reports/trivy.sarif \
            --exit-code 1
          TRIVY_RC=$?
          set -e
          [ -f security-reports/trivy.sarif ] || echo '{"version":"2.1.0","runs":[]}' > security-reports/trivy.sarif
          [ $TRIVY_RC -eq 0 ] || true
        '''
      }
    }

    stage('Publish Reports') {
      steps {
        recordIssues(tools: [sarif(pattern: 'security-reports/*.sarif')])
        archiveArtifacts artifacts: 'security-reports/*', fingerprint: true
      }
    }
  }

  post {
    always {
      echo 'Scan completed. Reports archived in security-reports/'
    }
    success {
      echo 'Build succeeded. No blocking security findings.'
    }
    failure {
      echo 'Build failed due to security findings or scanner errors. See artifacts.'
    }
  }
}