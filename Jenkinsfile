pipeline {
    agent any

    environment {
        IMAGE_TAG = "1.0.${BUILD_NUMBER}"
        TRIVY_CACHE_DIR = "/tmp/trivy-cache"
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'develop',
                    credentialsId: 'github-ssh',
                    url: 'git@github.com:ikramboussouifa-sys/devops-enterprise-project.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                python3 -m venv venv
                . venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }

        stage('Start Test DB') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'postgres-db-creds',
                    usernameVariable: 'DB_USER',
                    passwordVariable: 'DB_PASS'
                )]) {
                    sh '''
                    docker rm -f test-postgres || true

                    docker network ls | grep devops-enterprise-project_default || \
                    docker network create devops-enterprise-project_default

                    docker run -d \
                      --name test-postgres \
                      --network devops-enterprise-project_default \
                      -e POSTGRES_DB=devopsdb \
                      -e POSTGRES_USER=$DB_USER \
                      -e POSTGRES_PASSWORD=$DB_PASS \
                      postgres:17

                    sleep 20
                    '''
                }
            }
        }

        stage('Run Tests') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'postgres-db-creds',
                    usernameVariable: 'DB_USER',
                    passwordVariable: 'DB_PASS'
                )]) {
                    sh '''
                    . venv/bin/activate
                    export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@test-postgres:5432/devopsdb"
                    pytest
                    '''
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'sonar-scanner'

                    withSonarQubeEnv('sonarqube') {
                        sh """
                        . venv/bin/activate
                        ${scannerHome}/bin/sonar-scanner
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    docker build \
                      -t $DOCKER_USER/devops-api:$IMAGE_TAG \
                      -t $DOCKER_USER/devops-api:latest \
                      .
                    '''
                }
            }
        }

        stage('Trivy Security Scan') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    mkdir -p $TRIVY_CACHE_DIR

                    trivy image \
                      --cache-dir $TRIVY_CACHE_DIR \
                      --exit-code 1 \
                      --severity CRITICAL,HIGH \
                      --ignore-unfixed \
                      $DOCKER_USER/devops-api:$IMAGE_TAG
                    '''
                }
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    retry(3) {
                        sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                        docker push $DOCKER_USER/devops-api:$IMAGE_TAG
                        docker push $DOCKER_USER/devops-api:latest
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker rm -f test-postgres || true'
        }
    }
}