#!/bin/sh

rm -f my-deployment-package.zip
cd package
zip -r ../my-deployment-package.zip .
cd ..
zip my-deployment-package.zip lambda_function.py