pipeline {

    agent any

    environment {
        IMAGE_TAG = "1.0.${BUILD_NUMBER}"
        DB_CREDENTIALS = credentials('postgres-db-creds')
        DATABASE_URL = "postgresql://${DB_CREDENTIALS_USR}:${DB_CREDENTIALS_PSW}@test-postgres:5432/devopsdb"
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
                sh '''
                docker rm -f test-postgres || true

                docker network ls | grep devops-enterprise-project_default || \
                docker network create devops-enterprise-project_default

                docker run -d \
                  --name test-postgres \
                  --network devops-enterprise-project_default \
                  -e POSTGRES_DB=devopsdb \
                  -e POSTGRES_USER=$DB_CREDENTIALS_USR \
                  -e POSTGRES_PASSWORD=$DB_CREDENTIALS_PSW \
                  postgres:17

                sleep 20
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                . venv/bin/activate
                export DATABASE_URL=$DATABASE_URL
                pytest
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'sonar-scanner'
                    withSonarQubeEnv('sonarqube') {
                        sh """
                        . venv/bin/activate
                        ${scannerHome}/bin/sonar-scanner \
                          -Dsonar.projectKey=devops-api \
                          -Dsonar.projectName=devops-api \
                          -Dsonar.sources=. \
                          -Dsonar.python.version=3
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

        stage('Stop Test DB') {
            steps {
                sh '''
                docker rm -f test-postgres || true
                '''
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
                    export IMAGE_NAME=$DOCKER_USER/devops-api
                    docker build -t $IMAGE_NAME:$IMAGE_TAG .
                    '''
                }
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
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
                    sh '''
                    export IMAGE_NAME=$DOCKER_USER/devops-api
                    docker push $IMAGE_NAME:$IMAGE_TAG
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
            docker rm -f test-postgres || true
            '''
        }
    }
}