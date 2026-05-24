pipeline {

    agent any

    environment {
        IMAGE_NAME = "ikramboussouifa-sys/devops-api"
        IMAGE_TAG = "1.0.${BUILD_NUMBER}"

        // test database connection (used by pytest)
        DATABASE_URL = "postgresql://postgres:DevOps123!@test-postgres:5432/devopsdb"
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

                docker run -d \
                  --name test-postgres \
                  --network devops-enterprise-project_default \
                  -e POSTGRES_DB=devopsdb \
                  -e POSTGRES_USER=postgres \
                  -e POSTGRES_PASSWORD=DevOps123! \
                  postgres:17

                sleep 5
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

        stage('Stop Test DB') {
            steps {
                sh '''
                docker rm -f test-postgres || true
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                docker build -t $IMAGE_NAME:$IMAGE_TAG .
                '''
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {

                    sh '''
                    echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                    '''
                }
            }
        }

        stage('Docker Push') {
            steps {
                sh '''
                docker push $IMAGE_NAME:$IMAGE_TAG
                '''
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