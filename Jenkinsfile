pipeline {
  agent any

  environment {
    // สำคัญ: บังคับให้ docker client ในทุก stage ใช้ TCP 2375
    DOCKER_HOST = 'tcp://host.docker.internal:2375'
    // เผื่อเคยตั้ง TLS ไว้ที่ไหน ให้ล้างค่า
    DOCKER_TLS_VERIFY = ''
  }

  options {
    timestamps()
    ansiColor('xterm')
  }

  stages {
    stage('Sanity: Docker') {
      steps {
        sh '''
          set -e
          echo "DOCKER_HOST=$DOCKER_HOST"
          docker version
          docker ps
        '''
      }
    }

    // ตัวอย่าง stage สแกน (อย่าผูกกับ /var/run/docker.sock)
    stage('Semgrep (OWASP)') {
      steps {
        sh '''
          set -e
          docker run --rm -v "$PWD":/work -w /work python:3.11-slim bash -lc '
            apt-get update &&
            apt-get install -y --no-install-recommends git ca-certificates &&
            pip install --no-cache-dir semgrep &&
            semgrep scan --config=p/owasp-top-ten --config=p/python --include "**/*.py" --severity ERROR
          '
        '''
      }
    }
  }

  post {
    always {
      echo 'Scan completed. Reports archived in security-reports/'
    }
    failure {
      echo 'Build failed due to security findings or scanner errors. See artifacts.'
    }
  }
}
