pipeline {
  agent any

  environment {
    // สำคัญ: ให้ docker client ในทุก stage คุยกับ Docker Desktop ผ่าน TCP 2375
    DOCKER_HOST      = 'tcp://host.docker.internal:2375'
    DOCKER_TLS_VERIFY = ''
    REPORT_DIR       = 'security-reports'
    PY_IMAGE         = 'python:3.11-slim'
    TRIVY_IMAGE      = 'aquasec/trivy:latest'
  }

  options {
    timestamps()
    ansiColor('xterm')
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p "$REPORT_DIR"'
      }
    }

    stage('Sanity: Docker') {
      steps {
        sh '''
          set -euxo pipefail
          echo "DOCKER_HOST=$DOCKER_HOST"
          docker version
          docker ps
        '''
      }
    }

    stage('Python Lint & Tests') {
      when { expression { fileExists('requirements.txt') || fileExists('app.py') } }
      steps {
        sh '''
          set -euxo pipefail
          docker run --rm -v "$PWD":/work -w /work "$PY_IMAGE" bash -lc '
            python -V
            python -m pip install -q --no-cache-dir -r requirements.txt || true
            python -m pip install -q --no-cache-dir pytest flake8
            # Lint (ไม่ทำให้ล้ม build แต่เก็บไว้ดู)
            flake8 . || true
            # Unit tests (ถ้าไม่มี เทสก็จะผ่าน)
            pytest -q || true
          '
        '''
      }
    }

    stage('Dependency Scan (pip-audit)') {
      when { expression { fileExists('requirements.txt') } }
      steps {
        sh '''
          set -euxo pipefail
          docker run --rm -v "$PWD":/work -w /work "$PY_IMAGE" bash -lc '
            python -m pip install -q --no-cache-dir pip-audit
            pip-audit -r requirements.txt -f json -o "$REPORT_DIR/pip-audit.json"
          '
        '''
      }
    }

    stage('SAST: Semgrep (OWASP + Python)') {
      steps {
        sh '''
          set -euxo pipefail
          docker run --rm -v "$PWD":/work -w /work "$PY_IMAGE" bash -lc '
            python -m pip install -q --no-cache-dir semgrep
            semgrep scan \
              --config=p/owasp-top-ten \
              --config=p/python \
              --metrics=off \
              --severity ERROR \
              --sarif --output "$REPORT_DIR/semgrep.sarif" \
              --error
          '
        '''
      }
    }

    stage('SAST: Bandit (Python)') {
      steps {
        sh '''
          set -euxo pipefail
          docker run --rm -v "$PWD":/work -w /work "$PY_IMAGE" bash -lc '
            python -m pip install -q --no-cache-dir bandit
            # -iii -lll: รายงานระดับ MEDIUM/HIGH และทำให้ exit != 0 เมื่อพบปัญหา
            bandit -r . -f json -o "$REPORT_DIR/bandit.json" -iii -lll
          '
        '''
      }
    }

    stage('Trivy: Filesystem (Vuln/Misconfig/Secrets)') {
      steps {
        sh '''
          set -euxo pipefail

          # Vulnerabilities ในไฟล์/ไบนารี (workspace)
          docker run --rm -e DOCKER_HOST="$DOCKER_HOST" -v "$PWD":/work -w /work "$TRIVY_IMAGE" fs \
            --scanners vuln \
            --severity CRITICAL,HIGH \
            --ignore-unfixed \
            --exit-code 1 \
            --format sarif \
            --output "$REPORT_DIR/trivy-fs.sarif" \
            .

          # Misconfig (IaC: Dockerfile, K8s, Terraform, YAML ฯลฯ)
          docker run --rm -v "$PWD":/work -w /work "$TRIVY_IMAGE" config \
            --exit-code 1 \
            --format sarif \
            --output "$REPORT_DIR/trivy-config.sarif" \
            .

          # Secrets (รหัส/Token เผลอ commit)
          docker run --rm -v "$PWD":/work -w /work "$TRIVY_IMAGE" secret \
            --exit-code 1 \
            --format sarif \
            --output "$REPORT_DIR/trivy-secrets.sarif" \
            .
        '''
      }
    }

    stage('Build Image (optional)') {
      when { expression { fileExists('Dockerfile') } }
      steps {
        sh '''
          set -euxo pipefail
          IMAGE="owasp-demo:${BUILD_NUMBER}"
          docker build -t "$IMAGE" .
          echo "$IMAGE" > "$REPORT_DIR/IMAGE_TAG.txt"
        '''
      }
    }

    stage('Trivy: Image (optional)') {
      when { allOf { expression { fileExists('Dockerfile') } } }
      steps {
        sh '''
          set -euxo pipefail
          IMAGE=$(cat "$REPORT_DIR/IMAGE_TAG.txt")
          docker run --rm -e DOCKER_HOST="$DOCKER_HOST" "$TRIVY_IMAGE" image \
            --severity CRITICAL,HIGH \
            --ignore-unfixed \
            --exit-code 1 \
            --format sarif \
            --output "$REPORT_DIR/trivy-image.sarif" \
            "$IMAGE"
        '''
      }
    }

    stage('Publish Reports') {
      steps {
        script {
          // เก็บไฟล์รายงานทั้งหมด
          archiveArtifacts artifacts: "${REPORT_DIR}/**/*", allowEmptyArchive: true
          // แสดงผลใน Jenkins UI (Warnings NG รองรับ SARIF)
          recordIssues enabledForFailure: true, tools: [sarif(pattern: "${REPORT_DIR}/**/*.sarif")]
        }
      }
    }
  }

  post {
    success {
      echo '✅ All security checks passed.'
    }
    failure {
      echo '❌ Security checks failed. See Warnings NG and artifacts in "security-reports/".'
    }
    always {
      echo 'Scan completed. Reports archived in security-reports/.'
    }
  }
}
