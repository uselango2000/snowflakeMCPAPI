FROM public.ecr.aws/lambda/python:3.13

# Copy function code
COPY snowflakelambda.py ${LAMBDA_TASK_ROOT}/
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Command to run the Lambda runtime interface emulator (if running locally)
CMD ["snowflakelambda.lambda_handler"]
