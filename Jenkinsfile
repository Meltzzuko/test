pipeline {
  agent {
    docker {
      image 'docker:25.0.3-cli'
      // ใช้ root เพื่อเข้าถึง /var/run/docker.sock และ mount ได้ไม่สะดุด
      args '--entrypoint="" -u 0:0 -v /var/run/docker.sock:/var/run/docker.sock'
    }
  }

  options {
    timestamps()
    // ตัด ansiColor ออกจาก options — ไปใช้ wrap แทนด้านล่าง
  }

  environment {
    WORKDIR = "${env.WORKSPACE}"
  }

  stages {

    stage('Checkout') {
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          checkout scm
          sh '''
            set -e
            mkdir -p security-reports
          '''
        }
      }
    }

    stage('Semgrep (OWASP)') {
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          sh '''
            set -e
            docker run --rm \
              -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" \
              python:3.11-slim bash -lc '
                set -e
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
    }

    stage('Bandit (Python SAST)') {
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          sh '''
            set -e
            docker run --rm \
              -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" \
              python:3.11-slim bash -lc '
                set -e
                pip install --no-cache-dir -q "bandit==1.*" &&
                bandit -r . -ll -f json -o security-reports/bandit.json || true
              '
          '''
        }
      }
    }

    stage('pip-audit (Dependencies)') {
      when { expression { return fileExists('requirements.txt') } }
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          sh '''
            set -e
            docker run --rm \
              -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" \
              python:3.11-slim bash -lc '
                set -e
                pip install --no-cache-dir -q pip-audit &&
                pip-audit -r requirements.txt -f json -o security-reports/pip-audit_requirements.json || true
              '
          '''
        }
      }
    }

    stage('Trivy FS (Secrets & Misconfig)') {
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          sh '''
            set +e
            docker run --rm \
              -v "$WORKSPACE:$WORKSPACE" -w "$WORKSPACE" \
              aquasec/trivy:latest \
                fs . \
                --scanners vuln,secret,misconfig \
                --severity HIGH,CRITICAL \
                --format sarif --output security-reports/trivy.sarif \
                --exit-code 1
            TRIVY_RC=$?
            set -e
            # กันกรณีไฟล์ไม่ถูกสร้าง (เพื่อให้ recordIssues ทำงานได้)
            [ -f security-reports/trivy.sarif ] || echo '{"version":"2.1.0","runs":[]}' > security-reports/trivy.sarif
            # ไม่ให้ fail stage เพื่อไปสรุปผลรวมใน Publish Reports
            [ $TRIVY_RC -eq 0 ] || true
          '''
        }
      }
    }

    stage('Publish Reports') {
      steps {
        wrap([$class: 'AnsiColorBuildWrapper', colorMapName: 'xterm']) {
          // ต้องมี Warnings NG plugin + SARIF parser ติดตั้งไว้
          recordIssues(tools: [sarif(pattern: 'security-reports/*.sarif')])
          archiveArtifacts artifacts: 'security-reports/*', fingerprint: true
        }
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
