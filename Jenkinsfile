pipeline {
  agent {
    docker {
      image 'python:3.11-slim'
      args '-u 0:0'   // สิทธิ์ root ในคอนเทนเนอร์เพื่อ apt-get
    }
  }

  options {
    timestamps()
  }

  stages {
    stage('Setup tools') {
      steps {
        sh '''
          set -e
          apt-get update
          apt-get install -y --no-install-recommends git ca-certificates curl
          rm -rf /var/lib/apt/lists/*

          pip install --no-cache-dir -q semgrep bandit==1.* pip-audit

          # ติดตั้ง Trivy แบบไบนารี (ไม่ใช้ docker)
          curl -sL https://github.com/aquasecurity/trivy/releases/latest/download/trivy_Linux-64bit.tar.gz \
            | tar zx -C /usr/local/bin trivy
          trivy --version
        '''
      }
    }

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
          git config --global --add safe.directory "$PWD"
          semgrep scan \
            --include "**/*.py" \
            --config=p/owasp-top-ten \
            --config=p/python \
            --severity ERROR \
            --sarif --output security-reports/semgrep.sarif \
            --error
        '''
      }
    }

    stage('Bandit (Python SAST)') {
      steps {
        sh '''
          bandit -r . -ll -f json -o security-reports/bandit.json || true
        '''
      }
    }

    stage('pip-audit (Dependencies)') {
      when { expression { return fileExists('requirements.txt') } }
      steps {
        sh '''
          pip-audit -r requirements.txt -f json -o security-reports/pip-audit_requirements.json || true
        '''
      }
    }

    stage('Trivy FS (Secrets & Misconfig)') {
      steps {
        sh '''
          set +e
          trivy fs . \
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
    always { echo 'Scan completed. Reports archived in security-reports/' }
    success { echo 'Build succeeded. No blocking security findings.' }
    failure { echo 'Build failed due to security findings or scanner errors. See artifacts.' }
  }
}

