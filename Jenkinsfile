pipeline {

    agent {
         label '!rtp-wapl-bld84.cisco.com && !rtp-wapl-bld88.cisco.com && !rtp-wapl-bld95.cisco.com'
    }

    tools {
         jdk 'JDK11'
    }

    environment {
         BUILD_NAME = "${env.JOB_NAME.split('/')[2]}"
         BRANCH_NAME = "${env.JOB_NAME.split('/')[3]}"
         CURRENT_STAGE = ""
         BUILD_TAG = versionFromBuildNumber(env.BUILD_NUMBER)
    }

    stages {
        stage('Upload to CodeArtifact') {

            steps {
                script {
                    publishToCodeArtifact()
                }
            }
        }
    }
}


// Helper function to generate version string
def versionFromBuildNumber(buildNumber) {
    if (buildNumber.length() <= 2) {
        return "v0.0.${buildNumber}"
    } else {
        return "v0.${buildNumber[0]}.${buildNumber[1..buildNumber.length()-1]}"
    }
}

// Function to publish packages to CodeArtifact
def publishToCodeArtifact() {
    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', 
        accessKeyVariable: 'AWS_ACCESS_KEY_ID', 
        secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', 
        credentialsId: 'LCP_AWS_CODE_ARTIFACT']]) {

        docker.image("amazon/aws-cli:latest").inside("--entrypoint='' --privileged -u root --env AWS_DEFAULT_REGION=${AWS_ECR_REGION}") { 
            script {
                ensureCodeArtifactRepositoryExists()
                sh """
                    chmod +x ./build.sh && ./build.sh
                """
                publishPackagesWithPoetry()
            }
        }
    }
}


// Function to ensure the CodeArtifact repository exists
def ensureCodeArtifactRepositoryExists() {
    
    def repoExists = sh(script: """
        aws codeartifact describe-repository \
            --domain $ARTIFACTORY_DOMAIN \
            --domain-owner $ARTIFACTORY_OWNER \
            --repository ${BUILD_NAME} \
            --region $ARTIFACTORY_REGION \
            --query 'repository.repositoryName' \
            --output text || echo 'notfound'
    """, returnStdout: true).trim()

    if (repoExists == 'notfound') {
        echo "Repository does not exist, creating it now..."
        sh """
            aws codeartifact create-repository \
                --domain $ARTIFACTORY_DOMAIN \
                --domain-owner $ARTIFACTORY_OWNER \
                --repository ${BUILD_NAME} \
                --region $ARTIFACTORY_REGION
        """
    } else {
        echo "Repository already exists"
    }
}


// Function to publish the packages
def publishPackages() {
    sh """
        for file in \$(ls dist/*); do
            sha256sum=\$(sha256sum "\$file" | awk '{print \$1}')
            aws codeartifact publish-package-version \
                --domain $ARTIFACTORY_DOMAIN \
                --domain-owner $ARTIFACTORY_OWNER \
                --repository ${BUILD_NAME} \
                --format generic \
                --namespace ${BUILD_NAME} \
                --package \$(basename "\$file") \
                --package-version ${BUILD_TAG} \
                --asset-content \$file \
                --asset-name \$(basename "\$file") \
                --asset-sha256 \$sha256sum \
                --region $ARTIFACTORY_REGION
        done
    """
}

// Function to publish the packages using Poetry
def publishPackagesWithPoetry() {
    sh """
        export CODEARTIFACT_AUTH_TOKEN=\$(aws codeartifact get-authorization-token --domain $ARTIFACTORY_DOMAIN --domain-owner $ARTIFACTORY_OWNER --region $ARTIFACTORY_REGION --query authorizationToken --output text)
        poetry config repositories.codeartifact https://$ARTIFACTORY_DOMAIN-$ARTIFACTORY_OWNER.d.codeartifact.$ARTIFACTORY_REGION.amazonaws.com/pypi/${BUILD_NAME}/
        poetry config http-basic.codeartifact aws \$CODEARTIFACT_AUTH_TOKEN
        poetry publish -r codeartifact --no-interaction
    """
}