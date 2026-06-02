pipeline {

    agent any

    environment {
        IMAGE_TAG        = "1.0.${BUILD_NUMBER}"
        TRIVY_CACHE_DIR  = "/tmp/trivy-cache"
        K8S_NAMESPACE    = "devops"
        DEPLOYMENT_NAME  = "devops-api"
        CONTAINER_NAME   = "devops-api"
    }

    stages {

        // ─────────────────────────────────────────────
        // 1. SOURCE
        // ─────────────────────────────────────────────
        stage('Checkout') {
            steps {
                git branch: 'develop',
                    credentialsId: 'github-ssh',
                    url: 'git@github.com:ikramboussouifa-sys/devops-enterprise-project.git'
            }
        }

        // ─────────────────────────────────────────────
        // 2. BUILD
        // ─────────────────────────────────────────────
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

        // ─────────────────────────────────────────────
        // 3. TESTS
        // ─────────────────────────────────────────────
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

        // ─────────────────────────────────────────────
        // 4. QUALITE CODE
        // ─────────────────────────────────────────────
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

        // ─────────────────────────────────────────────
        // 5. IMAGE DOCKER
        // ─────────────────────────────────────────────
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
                    trivy image \
                      --exit-code 1 \
                      --severity CRITICAL \
                      --ignorefile .trivyignore \
                      --cache-dir $TRIVY_CACHE_DIR \
                      --format json \
                      --output trivy-report.json \
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

        // ─────────────────────────────────────────────
        // 6. DEPLOY KUBERNETES
        // ─────────────────────────────────────────────
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    ),
                    usernamePassword(
                        credentialsId: 'postgres-db-creds',
                        usernameVariable: 'DB_USER',
                        passwordVariable: 'DB_PASS'
                    )
                ]) {
                    sh '''
                    # 1. Namespace
                    kubectl get namespace $K8S_NAMESPACE || \
                    kubectl create namespace $K8S_NAMESPACE

                    # 2. Secret DB (upsert)
                    kubectl create secret generic devops-api-secret \
                      --namespace=$K8S_NAMESPACE \
                      --from-literal=DATABASE_URL="postgresql://$DB_USER:$DB_PASS@postgres-service:5432/devopsdb" \
                      --dry-run=client -o yaml | kubectl apply -f -

                    # 3. Appliquer les manifests (image tag fixe dans deployment.yaml)
                    kubectl apply -f k8s/deployment.yaml --namespace=$K8S_NAMESPACE
                    kubectl apply -f k8s/service.yaml    --namespace=$K8S_NAMESPACE

                    # 4. Mettre à jour l'image avec le tag du build courant — Fix S6596
                    #    (le deployment.yaml reste propre avec un tag fixe pour SonarQube)
                    kubectl set image deployment/$DEPLOYMENT_NAME \
                      $CONTAINER_NAME=$DOCKER_USER/devops-api:$IMAGE_TAG \
                      --namespace=$K8S_NAMESPACE

                    # 5. Attendre que le rollout soit prêt (max 3 min)
                    kubectl rollout status deployment/$DEPLOYMENT_NAME \
                      --namespace=$K8S_NAMESPACE \
                      --timeout=180s
                    '''
                }
            }
        }
    }

    // ─────────────────────────────────────────────
    // POST
    // ─────────────────────────────────────────────
    post {
        always {
            sh 'docker rm -f test-postgres || true'
            archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
        }
        success {
            echo "✅ Pipeline terminé — image déployée : ${env.DOCKER_USER}/devops-api:${env.IMAGE_TAG}"
        }
        failure {
            echo "❌ Pipeline échoué — voir les logs ci-dessus"
        }
    }
}